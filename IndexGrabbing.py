"""
现货指数行情抓取脚本
使用 akshare 抓取上证/深证/沪深300 实时行情，每隔 INTERVAL 秒写入 SQLite
"""

import time, sqlite3
import akshare as ak

# ── 配置 ─────────────────────────────────────────────
INTERVAL = 5
DB_PATH  = r'D:\Desktop\SilverGrabbingScript\stock_data.db'

SYMBOLS = {
    'shzs':  '上证指数',
    'szcz':  '深证成指',
    'hs300': '沪深300',
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


def fetch_quotes():
    df = ak.stock_zh_index_spot_sina()
    df = df.set_index('指数名称')
    result = {}
    for key, name in SYMBOLS.items():
        if name in df.index:
            row = df.loc[name]
            result[key] = {
                'price': float(row['最新价']),
                'chg':   float(row['涨跌额']),
                'pct':   float(row['涨跌幅']),
            }
        else:
            result[key] = None
    return result


def save(con, ts, quotes):
    def _v(key, field):
        q = quotes.get(key)
        return q[field] if q else None

    con.execute(
        'INSERT INTO index_data VALUES (NULL,?,?,?,?,?,?,?,?,?,?)',
        (ts,
         _v('shzs',  'price'), _v('shzs',  'chg'), _v('shzs',  'pct'),
         _v('szcz',  'price'), _v('szcz',  'chg'), _v('szcz',  'pct'),
         _v('hs300', 'price'), _v('hs300', 'chg'), _v('hs300', 'pct'))
    )
    con.commit()


def main():
    con = sqlite3.connect(DB_PATH)
    init_db(con)

    print(f'指数行情抓取启动，间隔={INTERVAL}s，DB={DB_PATH}')
    print('Ctrl+C 停止\n')

    count = 0
    try:
        while True:
            try:
                quotes = fetch_quotes()
                ts = time.strftime('%Y-%m-%d %H:%M:%S')
                save(con, ts, quotes)
                count += 1

                def _f(key):
                    q = quotes.get(key)
                    return f"{q['price']:.2f}({q['pct']:+.2f}%)" if q else '?'

                print(f'[{ts}] #{count:4d}  '
                      f'上证={_f("shzs")}  '
                      f'深证={_f("szcz")}  '
                      f'沪深300={_f("hs300")}')

            except Exception as e:
                print(f'[ERR {time.strftime("%H:%M:%S")}] {e}')

            time.sleep(INTERVAL)

    except KeyboardInterrupt:
        print('\n停止抓取')
    finally:
        con.close()


if __name__ == '__main__':
    main()
