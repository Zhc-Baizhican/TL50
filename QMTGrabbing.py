"""
股指期货 Tick 数据抓取脚本
使用 QMT（迅投）xtquant 订阅 IF/IH/IC/IM 四个品种实时 Tick，写入 SQLite

运行前提：
1. 华泰 QMT 客户端（MiniQMT）已登录并在后台运行
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
        open_int    INTEGER
    )''')
    con.commit()


def make_callback(con, symbol):
    def on_tick(data):
        tick = data.get(symbol)
        if not tick:
            return
        ts = time.strftime('%Y-%m-%d %H:%M:%S')
        try:
            bid_p = tick.get('bidPrice', [None]*5)
            bid_v = tick.get('bidVol',   [None]*5)
            ask_p = tick.get('askPrice', [None]*5)
            ask_v = tick.get('askVol',   [None]*5)

            def _p(lst, i): return lst[i] if lst and len(lst) > i else None

            con.execute(
                '''INSERT INTO qmt_tick VALUES
                (NULL,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                (ts, symbol,
                 tick.get('lastPrice'),
                 _p(bid_p,0), _p(bid_v,0),
                 _p(bid_p,1), _p(bid_v,1),
                 _p(bid_p,2), _p(bid_v,2),
                 _p(bid_p,3), _p(bid_v,3),
                 _p(bid_p,4), _p(bid_v,4),
                 _p(ask_p,0), _p(ask_v,0),
                 _p(ask_p,1), _p(ask_v,1),
                 _p(ask_p,2), _p(ask_v,2),
                 _p(ask_p,3), _p(ask_v,3),
                 _p(ask_p,4), _p(ask_v,4),
                 tick.get('volume'),
                 tick.get('amount'),
                 tick.get('openInt'))
            )
            con.commit()
            print(f'[{ts}] {symbol}  '
                  f'最新={tick.get("lastPrice")}  '
                  f'买一={_p(bid_p,0)}×{_p(bid_v,0)}  '
                  f'卖一={_p(ask_p,0)}×{_p(ask_v,0)}  '
                  f'持仓={tick.get("openInt")}')
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
