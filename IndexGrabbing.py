"""
现货指数行情抓取脚本
使用 TqSdk 订阅上证/深证/沪深300 实时行情，每隔 INTERVAL 秒写入 SQLite
"""

import time, sqlite3, threading
from tqsdk import TqApi, TqAuth

# ── 配置 ─────────────────────────────────────────────
INTERVAL = 5
DB_PATH  = r'D:\Desktop\SilverGrabbingScript\stock_data.db'
TQ_USER  = 'Mohai'
TQ_PASS  = '4510@Tqsdk'

SYMBOLS = {
    'shzs':  'SSE.000001',    # 上证指数
    'szcz':  'SZSE.399001',   # 深证成指
    'hs300': 'SZSE.399300',   # 沪深300
}
# ─────────────────────────────────────────────────────


def init_db(con):
    con.execute('''CREATE TABLE IF NOT EXISTS index_data (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        ts          TEXT NOT NULL,
        shzs_price  REAL, shzs_chg  REAL, shzs_pct  REAL,
        szcz_price  REAL, szcz_chg  REAL, szcz_pct  REAL,
        hs300_price REAL, hs300_chg REAL, hs300_pct REAL
    )''')
    con.commit()


def save(con, ts, quotes):
    def _v(sym, field):
        q = quotes.get(sym)
        return getattr(q, field, None) if q else None

    con.execute(
        'INSERT INTO index_data VALUES (NULL,?,?,?,?,?,?,?,?,?,?)',
        (ts,
         _v('shzs',  'last_price'), _v('shzs',  'change'), _v('shzs',  'change_rate'),
         _v('szcz',  'last_price'), _v('szcz',  'change'), _v('szcz',  'change_rate'),
         _v('hs300', 'last_price'), _v('hs300', 'change'), _v('hs300', 'change_rate'))
    )
    con.commit()


def main():
    api = TqApi(auth=TqAuth(TQ_USER, TQ_PASS))
    quotes = {key: api.get_quote(sym) for key, sym in SYMBOLS.items()}

    con = init_db_con = sqlite3.connect(DB_PATH)
    init_db(con)

    print(f'指数行情抓取启动，间隔={INTERVAL}s，DB={DB_PATH}')
    print('Ctrl+C 停止\n')

    count = 0
    try:
        while True:
            deadline = time.time() + INTERVAL
            # 等到下一个周期或有行情更新
            while time.time() < deadline:
                api.wait_update(deadline=deadline)

            ts = time.strftime('%Y-%m-%d %H:%M:%S')
            save(con, ts, quotes)
            count += 1

            shzs  = quotes['shzs']
            szcz  = quotes['szcz']
            hs300 = quotes['hs300']
            print(f'[{ts}] #{count:4d}  '
                  f'上证={shzs.last_price:.2f}({shzs.change_rate*100:+.2f}%)  '
                  f'深证={szcz.last_price:.2f}({szcz.change_rate*100:+.2f}%)  '
                  f'沪深300={hs300.last_price:.2f}({hs300.change_rate*100:+.2f}%)')

    except KeyboardInterrupt:
        print('\n停止抓取')
    finally:
        api.close()
        con.close()


if __name__ == '__main__':
    main()
