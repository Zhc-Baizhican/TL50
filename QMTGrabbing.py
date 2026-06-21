"""
股指期货 Tick 数据抓取脚本
使用 QMT（迅投）xtquant 订阅 IF/IH/IC/IM 四个品种实时 Tick，写入 SQLite

运行前提：
1. 华泰 QMT 客户端已登录并在后台运行
2. xtquant 已复制到 Python site-packages
"""

import sqlite3, time
from xtquant import xtdata

# ── 配置 ─────────────────────────────────────────────
DB_PATH = r'D:\Desktop\SilverGrabbingScript\stock_data.db'

# 四个品种的主力合约，每次换月时更新这里
CONTRACTS = [
    'IF2509.CFE',
    'IH2509.CFE',
    'IC2509.CFE',
    'IM2509.CFE',
]
# ─────────────────────────────────────────────────────


def init_db(con):
    con.execute('''CREATE TABLE IF NOT EXISTS qmt_tick (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        ts          TEXT NOT NULL,
        symbol      TEXT NOT NULL,
        last_price  REAL,
        bid1        REAL, bid1_vol INTEGER,
        bid2        REAL, bid2_vol INTEGER,
        bid3        REAL, bid3_vol INTEGER,
        bid4        REAL, bid4_vol INTEGER,
        bid5        REAL, bid5_vol INTEGER,
        ask1        REAL, ask1_vol INTEGER,
        ask2        REAL, ask2_vol INTEGER,
        ask3        REAL, ask3_vol INTEGER,
        ask4        REAL, ask4_vol INTEGER,
        ask5        REAL, ask5_vol INTEGER,
        volume      INTEGER,
        amount      REAL,
        open_interest INTEGER
    )''')
    con.commit()


def make_callback(con, symbol):
    def on_tick(data):
        ts = time.strftime('%Y-%m-%d %H:%M:%S')
        try:
            con.execute(
                '''INSERT INTO qmt_tick VALUES
                (NULL,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                (ts, symbol,
                 data.get('lastPrice'),
                 data.get('bidPrice1'), data.get('bidVol1'),
                 data.get('bidPrice2'), data.get('bidVol2'),
                 data.get('bidPrice3'), data.get('bidVol3'),
                 data.get('bidPrice4'), data.get('bidVol4'),
                 data.get('bidPrice5'), data.get('bidVol5'),
                 data.get('askPrice1'), data.get('askVol1'),
                 data.get('askPrice2'), data.get('askVol2'),
                 data.get('askPrice3'), data.get('askVol3'),
                 data.get('askPrice4'), data.get('askVol4'),
                 data.get('askPrice5'), data.get('askVol5'),
                 data.get('volume'),
                 data.get('amount'),
                 data.get('openInterest'))
            )
            con.commit()
            print(f'[{ts}] {symbol}  '
                  f'最新={data.get("lastPrice")}  '
                  f'买一={data.get("bidPrice1")}×{data.get("bidVol1")}  '
                  f'卖一={data.get("askPrice1")}×{data.get("askVol1")}  '
                  f'持仓={data.get("openInterest")}')
        except Exception as e:
            print(f'[ERR] {e}')
    return on_tick


def main():
    con = sqlite3.connect(DB_PATH)
    init_db(con)

    print(f'QMT Tick 抓取启动，合约={CONTRACTS}')
    print('Ctrl+C 停止\n')

    for symbol in CONTRACTS:
        xtdata.subscribe_quote(symbol, period='tick',
                               callback=make_callback(con, symbol))

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print('\n停止抓取')
    finally:
        for symbol in CONTRACTS:
            xtdata.unsubscribe_quote(symbol)
        con.close()


if __name__ == '__main__':
    main()
