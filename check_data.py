import sqlite3

DB_FILE = "market_data.db"

conn = sqlite3.connect(DB_FILE)
rows = conn.execute("""
    SELECT recv_time, instrument_id, last_price, volume, bid_price1, ask_price1, update_time
    FROM tick_data
    ORDER BY id DESC
    LIMIT 10
""").fetchall()
conn.close()

if not rows:
    print("数据库为空，请先运行 market_data.py 收集数据。")
else:
    print(f"{'接收时间':<22} {'合约':<10} {'最新价':>10} {'成交量':>10} {'买一':>10} {'卖一':>10} {'交易所时间'}")
    print("-" * 90)
    for r in rows:
        print(f"{r[0]:<22} {r[1]:<10} {r[2]:>10.2f} {r[3]:>10} {r[4]:>10.2f} {r[5]:>10.2f} {r[6]}")
