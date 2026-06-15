"""
野狼3000 数据抓取脚本 v3
每隔 INTERVAL 秒截图一次，OCR提取指标，存入SQLite
运行要求：管理员权限
"""

import win32gui, win32ui, ctypes, time, sqlite3, re, io, os
import numpy as np
from PIL import Image

# ── 配置 ─────────────────────────────────────────────
INTERVAL   = 2
DB_PATH    = r'D:\Desktop\SilverGrabbingScript\stock_data.db'
DEBUG_SAVE = False
DEBUG_DIR  = r'D:\Desktop\SilverGrabbingScript\yl_debug'
# ─────────────────────────────────────────────────────

ctypes.windll.user32.SetProcessDPIAware()

import ddddocr
_ocr = ddddocr.DdddOcr(show_ad=False)


# ══ 1. 截图 ══════════════════════════════════════════

def find_hwnd():
    result = []
    def cb(hwnd, _):
        t = win32gui.GetWindowText(hwnd)
        if '天狼' in t or '野狼' in t or 'TL50' in t:
            result.append(hwnd)
    win32gui.EnumWindows(cb, None)
    if not result:
        raise RuntimeError('找不到野狼3000窗口')
    return result[0]

def capture_window():
    hwnd = find_hwnd()
    win32gui.ShowWindow(hwnd, 4)
    time.sleep(0.3)
    l, t, r, b = win32gui.GetWindowRect(hwnd)
    w, h = r - l, b - t
    hdc = win32gui.GetWindowDC(hwnd)
    mdc = win32ui.CreateDCFromHandle(hdc)
    bdc = mdc.CreateCompatibleDC()
    bmp = win32ui.CreateBitmap()
    bmp.CreateCompatibleBitmap(mdc, w, h)
    bdc.SelectObject(bmp)
    ctypes.windll.user32.PrintWindow(hwnd, bdc.GetSafeHdc(), 2)
    info = bmp.GetInfo()
    data = bmp.GetBitmapBits(True)
    img = Image.frombuffer('RGB', (info['bmWidth'], info['bmHeight']),
                           data, 'raw', 'BGRX', 0, 1)
    bdc.DeleteDC(); mdc.DeleteDC(); win32gui.ReleaseDC(hwnd, hdc)
    return img


# ══ 2. OCR辅助 ═══════════════════════════════════════

def _to_png(arr_rgb):
    buf = io.BytesIO()
    Image.fromarray(arr_rgb.astype(np.uint8)).save(buf, format='PNG')
    return buf.getvalue()

def ocr_bright(arr, x1, y1, x2, y2, thr=120):
    p = arr[y1:y2, x1:x2]
    m = p.max(axis=2) > thr
    return _ocr.classification(_to_png(np.where(m[:,:,None], [0,0,0], [255,255,255])))

def first_int(raw, min_len=2):
    for m in re.finditer(r'\d+', raw):
        if len(m.group()) >= min_len:
            return m.group()
    return None


# ══ 3. 区域坐标（物理像素，基于1750×1225截图）════════

_R = {
    'wtb':       (90,  650, 500,  682),   # 委托比[正向]
    'wte_sell':  (270, 800, 390,  836),   # 委卖额 ÷100=亿
    'wte_buy':   (450, 800, 570,  836),   # 委买额 ÷100=亿
    'fyx_feng':  (445, 950, 560,  986),   # 风 ÷100=亿
    'fyx_yu':    (555, 950, 750,  986),   # 雨 ÷100=亿（宽截取保留尾0）
    'pmzj_fund': (260, 503, 360,  535),   # 盘面资金 取前4位=整数亿
    'pmzj_avg':  (450, 503, 580,  535),   # 均值 取前4位
}


# ══ 4. 提取指标 ══════════════════════════════════════

def _in(val, lo, hi):
    """范围校验，超出则返回 None"""
    return val if (val is not None and lo <= val <= hi) else None

def extract_all(img):
    arr = np.array(img)
    d   = {}

    def _get(key, div=100):
        n = first_int(ocr_bright(arr, *_R[key]), min_len=3)
        return round(float(n) / div, 2) if n else None

    # 委托比[正向]
    raw = ocr_bright(arr, *_R['wtb']).replace(',', '.').replace('，', '.')
    m = re.search(r'\d+\.\d+', raw)
    if m:
        v = float(m.group())
        if 0 <= v <= 5:
            d['wtb'] = round(v, 2)
    if 'wtb' not in d:
        for n in re.findall(r'\d+', raw):
            if 2 <= len(n) <= 4:
                v = float(n) / (100 if len(n) >= 3 else 1)
                if 0 <= v <= 5:
                    d['wtb'] = round(v, 2); break

    # 委托额
    sell = _in(_get('wte_sell'), 100, 5000)
    buy  = _in(_get('wte_buy'),  100, 5000)
    if sell is not None: d['wt_sell'] = sell
    if buy  is not None: d['wt_buy']  = buy
    if sell is not None and buy is not None:
        d['wt_diff'] = round(buy - sell, 2)

    # 风雨线（要求至少4位数字，确保小数部分被读入）
    def _get4(key):
        n = first_int(ocr_bright(arr, *_R[key]), min_len=4)
        return round(float(n) / 100, 2) if n else None

    feng   = _in(_get4('fyx_feng'), 0, 2000)
    yu_abs = _in(_get4('fyx_yu'),   0, 2000)
    if feng   is not None: d['fyx_feng']  = feng
    if yu_abs is not None: d['fyx_yu']    = -yu_abs
    if feng   is not None and yu_abs is not None:
        d['fyx_total'] = round(feng - yu_abs, 2)

    # 盘面资金
    n = first_int(ocr_bright(arr, *_R['pmzj_fund'], thr=80), 4)
    if n:
        v = int(n[:4])
        if 1000 <= v <= 30000: d['pmzj_fund'] = v
    n = first_int(ocr_bright(arr, *_R['pmzj_avg']), 4)
    if n:
        v = int(n[:4])
        if 1000 <= v <= 30000: d['pmzj_avg'] = v

    return d


# ══ 5. SQLite存储 ═════════════════════════════════════

def init_db():
    con = sqlite3.connect(DB_PATH)
    con.execute('''CREATE TABLE IF NOT EXISTS yl_data (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        ts        TEXT NOT NULL,
        wtb       REAL,
        wt_sell   REAL, wt_buy  REAL, wt_diff  REAL,
        fyx_total REAL, fyx_feng REAL, fyx_yu   REAL,
        pmzj_fund INTEGER, pmzj_avg INTEGER
    )''')
    con.commit()
    return con

def save_to_db(con, ts, d):
    con.execute(
        'INSERT INTO yl_data VALUES (NULL,?,?,?,?,?,?,?,?,?,?)',
        (ts,
         d.get('wtb'),
         d.get('wt_sell'), d.get('wt_buy'),  d.get('wt_diff'),
         d.get('fyx_total'), d.get('fyx_feng'), d.get('fyx_yu'),
         d.get('pmzj_fund'), d.get('pmzj_avg'))
    )
    con.commit()


# ══ 6. 主循环 ═════════════════════════════════════════

def main():
    if DEBUG_SAVE:
        os.makedirs(DEBUG_DIR, exist_ok=True)

    con   = init_db()
    count = 0
    print(f'野狼3000抓取启动，间隔={INTERVAL}s，DB={DB_PATH}')
    print('Ctrl+C 停止\n')

    while True:
        try:
            ts  = time.strftime('%Y-%m-%d %H:%M:%S')
            img = capture_window()
            if DEBUG_SAVE:
                img.save(os.path.join(DEBUG_DIR,
                         f'snap_{ts.replace(":","-").replace(" ","_")}.png'))

            d = extract_all(img)
            save_to_db(con, ts, d)
            count += 1

            def _f(val, fmt='.2f'):
                return format(val, fmt) if isinstance(val, (int, float)) else '?'

            print(f'[{ts}] #{count:4d}  '
                  f'资金={d.get("pmzj_fund","?")}亿  均值={d.get("pmzj_avg","?")}亿  '
                  f'委托比={d.get("wtb","?")}  '
                  f'委卖={_f(d.get("wt_sell"))}  委买={_f(d.get("wt_buy"))}  差={_f(d.get("wt_diff"),"+.2f")}  '
                  f'风={_f(d.get("fyx_feng"))}  雨={_f(d.get("fyx_yu"))}  合计={_f(d.get("fyx_total"),"+.2f")}亿')

        except KeyboardInterrupt:
            print('\n停止抓取')
            break
        except Exception as e:
            print(f'[ERR {time.strftime("%H:%M:%S")}] {e}')

        time.sleep(INTERVAL)

    con.close()

if __name__ == '__main__':
    main()
