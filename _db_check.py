import sqlite3, os
db = os.path.join(os.path.dirname(__file__), "backend", "dev.db")
con = sqlite3.connect(db)
cur = con.cursor()
tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
print("表:", tables)
for t in tables:
    n = cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    print(f"  {t}: {n} 行")
print("\n=== bot 表真实记录 ===")
for row in cur.execute("SELECT id,bot_name,ark_model_id,base_url,bot_switch,stream_enable FROM bot").fetchall():
    print(row)
