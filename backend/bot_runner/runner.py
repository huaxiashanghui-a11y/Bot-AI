"""多 Telegram Bot 进程管理：每个 Bot 独立 polling，配置/用户/对话从数据库实时读取。"""
import asyncio
import base64
import time
from datetime import date

import httpx
from telegram import Update
from telegram.ext import (ContextTypes, MessageHandler,
                          CommandHandler, filters)

from ..database import SessionLocal
from ..models import Bot, TgUser, ChatHistory, TokenStat, Keyword
from . import doubao_client

_running = {}        # bot_id -> {"app": Application, "stop_event": asyncio.Event}
_loop = None         # FastAPI 主事件循环

def set_loop(loop):
    global _loop
    _loop = loop

def running_ids():
    return list(_running.keys())

# ---------- 内部 async 实现 ----------
async def _launch(row: Bot):
    from telegram.ext import Application
    app = Application.builder().token(row.tg_bot_token).build()
    app.bot_data["bot_id"] = row.id
    app.add_handler(CommandHandler("start", _start_cmd))
    app.add_handler(CommandHandler("clear", _clear_cmd))
    app.add_handler(MessageHandler(filters.PHOTO, _on_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, _on_text))
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    evt = asyncio.Event()
    _running[row.id] = {"app": app, "stop_event": evt}
    await evt.wait()                       # 阻塞直到被停止
    await app.updater.stop()
    await app.stop()
    await app.shutdown()
    _running.pop(row.id, None)

async def _start_one(row: Bot):
    if row.id in _running:
        await _stop_one(row.id)
    asyncio.create_task(_launch(row))
    await asyncio.sleep(1.5)

async def _stop_one(bot_id: int):
    info = _running.pop(bot_id, None)
    if info:
        info["stop_event"].set()
        await asyncio.sleep(0.5)

async def startup_all():
    db = SessionLocal()
    try:
        rows = db.query(Bot).filter(Bot.bot_switch == True).all()  # noqa: E712
        for r in rows:
            try:
                await _start_one(r)
            except Exception as e:
                print(f"[runner] Bot#{r.id} 启动失败: {e}")
    finally:
        db.close()

async def shutdown_all():
    for bid in list(_running.keys()):
        try:
            await _stop_one(bid)
        except Exception:
            pass

# ---------- 供后台路由同步调用 ----------
def _sync(coro):
    if _loop is None:
        raise RuntimeError("服务尚未就绪")
    return asyncio.run_coroutine_threadsafe(coro, _loop).result(timeout=20)

def start_bot(row: Bot):
    return _sync(_start_one(row))

def stop_bot(bot_id: int):
    return _sync(_stop_one(bot_id))

def restart_bot(row: Bot):
    return _sync(_start_one(row))

# ---------- 公共小工具 ----------
def _get_or_create_user(db, bot_id, tg_user) -> TgUser:
    u = (db.query(TgUser)
         .filter(TgUser.bot_id == bot_id, TgUser.tg_user_id == tg_user.id).first())
    if not u:
        u = TgUser(bot_id=bot_id, tg_user_id=tg_user.id,
                   username=tg_user.username, first_name=tg_user.first_name,
                   last_name=tg_user.last_name)
        db.add(u); db.commit(); db.refresh(u)
    return u

def _recent_messages(db, bot_id, tg_user_id, limit):
    rows = (db.query(ChatHistory)
            .filter(ChatHistory.bot_id == bot_id, ChatHistory.tg_user_id == tg_user_id,
                    ChatHistory.role.in_(["user", "assistant"]))
            .order_by(ChatHistory.id.desc()).limit(limit * 2).all())
    return [{"role": r.role, "content": r.content} for r in reversed(rows)]

def _record_usage(bot_id, tg_user_id, assistant_text, usage):
    db = SessionLocal()
    try:
        in_tok = (usage or {}).get("prompt_tokens", 0)
        out_tok = (usage or {}).get("completion_tokens", 0)
        db.add(ChatHistory(bot_id=bot_id, tg_user_id=tg_user_id,
                           role="assistant", content=assistant_text, token_count=out_tok))
        u = (db.query(TgUser)
             .filter(TgUser.bot_id == bot_id, TgUser.tg_user_id == tg_user_id).first())
        if u:
            u.total_token_used += (in_tok + out_tok)
            u.remain_quota = max(0, u.remain_quota - (in_tok + out_tok))
        today = date.today()
        st = (db.query(TokenStat)
              .filter(TokenStat.bot_id == bot_id, TokenStat.stat_date == today).first())
        if not st:
            st = TokenStat(bot_id=bot_id, stat_date=today)
            db.add(st)
        st.total_input_tokens += in_tok
        st.total_output_tokens += out_tok
        st.total_request += 1
        db.commit()
    finally:
        db.close()

async def _reply_long(update, text):
    for i in range(0, len(text), 4000):
        await update.message.reply_text(text[i:i + 4000])

# ---------- 命令 ----------
async def _start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "你好！我是 AI 助手。\n· 直接发文字对话\n· 发图片 + 说明可识图\n· /clear 清空上下文")

async def _clear_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot_id = context.application.bot_data["bot_id"]
    tg_id = update.effective_user.id
    db = SessionLocal()
    try:
        db.query(ChatHistory).filter(ChatHistory.bot_id == bot_id,
                                     ChatHistory.tg_user_id == tg_id).delete()
        db.commit()
    finally:
        db.close()
    await update.message.reply_text("✅ 对话上下文已清空")

# ---------- 文本消息（支持流式） ----------
async def _on_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot_id = context.application.bot_data["bot_id"]
    text = update.message.text
    tg_user = update.effective_user

    db = SessionLocal()
    try:
        cfg = db.get(Bot, bot_id)
        if not cfg or not cfg.bot_switch:
            return
        u = _get_or_create_user(db, bot_id, tg_user)
        if u.is_black:
            await update.message.reply_text("您已被限制使用本服务。")
            return
        if u.remain_quota <= 0:
            await update.message.reply_text("您的额度已用完，请联系管理员。")
            return
        keywords = [k.word for k in db.query(Keyword).all()]
        if any(w and w in text for w in keywords):
            await update.message.reply_text("您的消息包含受限内容。")
            return

        messages = []
        if cfg.system_prompt:
            messages.append({"role": "system", "content": cfg.system_prompt})
        messages += _recent_messages(db, bot_id, tg_user.id, cfg.user_max_context_len)
        messages.append({"role": "user", "content": text})

        db.add(ChatHistory(bot_id=bot_id, tg_user_id=tg_user.id, role="user", content=text))
        db.commit()
        api_key, model = cfg.ark_api_key, cfg.ark_model_id
        temperature, max_tokens = cfg.temperature, cfg.max_tokens
        use_stream = cfg.stream_enable
        base_url = cfg.base_url or ""
    finally:
        db.close()

    if use_stream:
        full, final_usage = await _reply_streaming(update, messages, api_key, model,
                                                   temperature, max_tokens, base_url)
        if not full:
            return
    else:
        try:
            full, final_usage = await doubao_client.chat(messages, api_key, model,
                                                        temperature, max_tokens, base_url)
        except Exception as e:
            await update.message.reply_text(f"AI 服务暂时不可用：{type(e).__name__}")
            return
        await _reply_long(update, full)

    _record_usage(bot_id, tg_user.id, full, final_usage)

async def _reply_streaming(update, messages, api_key, model, temperature, max_tokens, base_url=""):
    """流式：先回一条占位消息，再定时编辑更新，模拟打字效果。返回(完整文本, usage)。"""
    sent = await update.message.reply_text("…")
    full = ""
    last_edit_at = 0.0
    last_shown = ""
    final_usage = None
    try:
        async for delta, usage in doubao_client.chat_stream(messages, api_key, model,
                                                            temperature, max_tokens, base_url):
            if usage:
                final_usage = usage
            if delta:
                full += delta
                now = time.time()
                if now - last_edit_at >= 1.2 and full != last_shown:
                    try:
                        await sent.edit_text(full[:4000])
                        last_edit_at = now
                        last_shown = full
                    except Exception:
                        pass
    except Exception as e:
        try:
            await sent.edit_text(f"AI 服务暂时不可用：{type(e).__name__}")
        except Exception:
            pass
        return "", final_usage
    final_text = full[:4000] if full else "(无回复)"
    try:
        await sent.edit_text(final_text)
    except Exception:
        pass
    return full, final_usage

# ---------- 图片消息（多模态识图） ----------
async def _on_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot_id = context.application.bot_data["bot_id"]
    tg_user = update.effective_user
    caption = update.message.caption or "请描述这张图片的内容"

    db = SessionLocal()
    try:
        cfg = db.get(Bot, bot_id)
        if not cfg or not cfg.bot_switch:
            return
        u = _get_or_create_user(db, bot_id, tg_user)
        if u.is_black:
            await update.message.reply_text("您已被限制使用本服务。")
            return
        if u.remain_quota <= 0:
            await update.message.reply_text("您的额度已用完，请联系管理员。")
            return
        if not cfg.vision_model_id:
            await update.message.reply_text("该 Bot 未配置视觉模型 ID，暂不支持识图。")
            return
        keywords = [k.word for k in db.query(Keyword).all()]
        if any(w and w in caption for w in keywords):
            await update.message.reply_text("您的消息包含受限内容。")
            return

        # 下载 TG 图片
        photo = update.message.photo[-1]
        tg_file = await context.bot.get_file(photo.file_id)
        file_url = f"https://api.telegram.org/file/bot{context.bot.token}/{tg_file.file_path}"
        async with httpx.AsyncClient(timeout=60) as c:
            r = await c.get(file_url)
            img_b64 = base64.b64encode(r.content).decode()

        messages = []
        if cfg.system_prompt:
            messages.append({"role": "system", "content": cfg.system_prompt})
        messages += _recent_messages(db, bot_id, tg_user.id, cfg.user_max_context_len)
        messages.append({"role": "user", "content": [
            {"type": "text", "text": caption},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}},
        ]})

        db.add(ChatHistory(bot_id=bot_id, tg_user_id=tg_user.id,
                           role="user", content=f"[图片] {caption}"))
        db.commit()
        api_key, vmodel = cfg.ark_api_key, cfg.vision_model_id
        temperature, max_tokens = cfg.temperature, cfg.max_tokens
        base_url = cfg.base_url or ""
    finally:
        db.close()

    try:
        reply, usage = await doubao_client.chat_vision(messages, api_key, vmodel,
                                                     temperature, max_tokens, base_url)
    except Exception as e:
        await update.message.reply_text(f"识图服务不可用：{type(e).__name__}")
        return
    await _reply_long(update, reply)
    _record_usage(bot_id, tg_user.id, reply, usage)
