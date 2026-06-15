# SilverGrabbingScript —— Claude 参考手册

> 本文档供 Claude 阅读，描述当前成品的完整状态，用于维护和二次开发。

---

## 系统概述

**目标**：定时抓取野狼3000（TL50V2.exe）软件界面上的汇总指标，存入本地 SQLite 数据库。

**方案**：截图 + 颜色过滤 + OCR，无需 API 或逆向协议。

**运行方式**：桌面快捷方式 `白银.lnk`，以管理员权限启动（野狼3000 本身以管理员运行，截图需要同权限）。

---

## 文件结构

```
D:\Desktop\SilverGrabbingScript\
├── SilverGrabbingScript.py          # 主脚本
├── stock_data.db             # SQLite 数据库
├── SilverGrabbingScript_ForClaude.md  # 本文档
└── yl_debug\
    ├── test.png              # 参考截图（1750×1225，校准坐标用）
    └── test_run.py           # 离线测试脚本（对 test.png 跑 extract_all）

D:\Desktop\
└── 白银.lnk                  # 桌面快捷方式（管理员权限）
```

---

## 技术栈

| 组件 | 说明 |
|---|---|
| `win32gui` / `win32ui` | 枚举窗口、PrintWindow 截图 |
| `ctypes.windll.user32.PrintWindow(hwnd, hdc, 2)` | 后台/最小化时也能截到完整画面 |
| `SetProcessDPIAware()` | 必须在所有 win32 操作前调用，否则坐标按缩放比例缩小 |
| `ddddocr` | OCR 识别（轻量 ONNX 模型，约 100MB 内存） |
| `numpy` | 颜色通道过滤，预处理图像 |
| `sqlite3` | 存储，表名 `yl_data` |

---

## 屏幕环境

- 物理分辨率：2560×1600
- DPI 缩放：175%
- 野狼3000 物理窗口尺寸：**1750×1225 px**（所有坐标基于此）
- 未调用 `SetProcessDPIAware()` 时 `GetWindowRect` 返回逻辑坐标 1000×700，截图不完整

---

## 配置参数（SilverGrabbingScript.py 顶部）

| 参数 | 当前值 | 说明 |
|---|---|---|
| `INTERVAL` | `5` | 抓取间隔（秒），可改为任意 ≥2 的值 |
| `DB_PATH` | `D:\Desktop\SilverGrabbingScript\stock_data.db` | 数据库路径 |
| `DEBUG_SAVE` | `False` | 改为 `True` 后每次把截图写入 `DEBUG_DIR` |
| `DEBUG_DIR` | `D:\Desktop\SilverGrabbingScript\yl_debug` | 调试截图保存目录 |

---

## 数据字段与坐标

### IF 主力合约买卖十档（`if_depth`）

绿色价格列，`ocr_green()` 提取（G>130, R<120, B<120 → 黑字白底）。

| 档位 | x1 | y1 | x2 | y2 |
|---|---|---|---|---|
| 卖五 | 1455 | 221 | 1685 | 252 |
| 卖四 | 1455 | 252 | 1685 | 283 |
| 卖三 | 1455 | 283 | 1685 | 314 |
| 卖二 | 1455 | 314 | 1685 | 345 |
| 卖一 | 1455 | 345 | 1685 | 376 |
| 买一 | 1455 | 378 | 1685 | 409 |
| 买二 | 1455 | 409 | 1685 | 440 |
| 买三 | 1455 | 440 | 1685 | 471 |
| 买四 | 1455 | 471 | 1685 | 502 |
| 买五 | 1455 | 502 | 1685 | 533 |

价格解析：OCR 常丢小数点，用 `re.search(r'(\d{4,5})[.,](\d)', raw)` 还原，结果为如 `3856.2`。

### 其他字段（`_R` 字典，`ocr_bright()` 提取）

| 字段 | 坐标 (x1,y1,x2,y2) | 单位/解析方式 | DB 列名 |
|---|---|---|---|
| IF涨跌幅 | (1390,178,1560,208) | 整数÷100=百分比；红像素>8→负 | `if_pct` |
| 委托比[正向] | (90,650,500,682) | 优先匹配带小数点；否则整数÷100 | `wtb` |
| 委卖额 | (270,800,390,836) | 整数÷100=亿 | `wt_sell` |
| 委买额 | (450,800,570,836) | 整数÷100=亿 | `wt_buy` |
| 风（正动力） | (445,950,560,986) | 整数÷100=亿 | `fyx_feng` |
| 雨（负动力） | (555,950,750,986) | 整数÷100=亿，存为负值 | `fyx_yu` |
| 盘面资金 | (260,503,360,535) | thr=80，取OCR结果前4位=整数亿 | `pmzj_fund` |
| 盘面均值 | (460,503,570,535) | thr=80，取OCR结果前4位（有OCR误差） | `pmzj_avg` |
| 底部指数行 | (0,1153,1250,1185) | 连续数字流，按固定位数切分 | 见下 |

### 底部指数行解析

OCR 返回连续中文+数字混合文本，按固定字数切分：

| 指数 | Regex | 价格位数 | 涨跌位数 | DB 列 |
|---|---|---|---|---|
| 上证指数 | `上证指数(\d{6})(\d{3})` | 6位÷100 | 3位÷100 | `shzs_price`, `shzs_chg` |
| 深证成指 | `深证成指(\d{7})(\d{4})` | 7位÷100 | 4位÷100 | `szcy_price`, `szcy_chg` |
| 沪深300 | `沪深\d{3}(\d{6})(\d{4})` | 6位÷100 | 4位÷100 | `hs300_price`, `hs300_chg` |

上证涨跌符号由 `is_red_region(arr, 330, 133, 580, 175)` 检测（红像素>15→负）。

---

## 数据库结构

**文件**：`D:\Desktop\SilverGrabbingScript\stock_data.db`  
**表**：`yl_data`

```sql
CREATE TABLE yl_data (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    ts           TEXT NOT NULL,          -- YYYY-MM-DD HH:MM:SS
    shzs_price   REAL, shzs_chg   REAL,
    szcy_price   REAL, szcy_chg   REAL,
    hs300_price  REAL, hs300_chg  REAL,
    if_pct       REAL,
    if_s5 REAL, if_s4 REAL, if_s3 REAL, if_s2 REAL, if_s1 REAL,
    if_b1 REAL, if_b2 REAL, if_b3 REAL, if_b4 REAL, if_b5 REAL,
    wtb          REAL,
    wt_sell      REAL, wt_buy REAL, wt_diff REAL,
    fyx_total    REAL, fyx_feng REAL, fyx_yu REAL,
    pmzj_fund    INTEGER, pmzj_avg INTEGER,
    raw_json     TEXT                    -- 完整提取结果备份
)
```

`wt_diff = wt_buy - wt_sell`（买-卖，通常为负）  
`fyx_total = fyx_feng - |fyx_yu|`（雨已存为负值）

---

## 重新校准坐标（界面布局改变时）

1. 将 `DEBUG_SAVE = True`，运行一次，在 `yl_debug\` 得到当前截图
2. 用图像查看器量出新字段的像素位置（x1,y1,x2,y2）
3. 更新 `_R` 字典和 `_DEPTH_COORDS`
4. 用 `yl_debug\test_run.py` 对新截图离线验证，确认各字段解析正确
5. 将 `DEBUG_SAVE` 改回 `False`

---

## 已知限制

- `pmzj_avg`（盘面均值）OCR 在该区域有稳定误差，存储值为近似值
- 底部指数行涨跌符号：深证/沪深300 直接取负值（实测与上证同向），未做颜色检测
- 合约代码（IF2606）硬编码在注释中，换月时需同步更新注释，坐标本身不变
