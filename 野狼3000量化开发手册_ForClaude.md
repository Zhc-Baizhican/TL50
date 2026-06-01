# 野狼3000股指期货数据抓取 —— Claude开发手册

> **本文档用途**：交给 Claude 阅读，让 Claude 一步步帮你完成代码开发。  
> **目标**：用 Python 通过 CTP 协议实时抓取股指期货行情数据，存入本地数据库。

---

## 背景说明（Claude必读）

**软件**：野狼3000（鼎信汇金），桌面客户端，用于股指期货分析  
**协议分析结论**：通过DLL分析确认，野狼3000期货行情走的是 **CTP协议**（上期技术标准接口），具体DLL为 `thostmduserapi_se.dll` 和 `thosttraderapi_se.dll`  
**结论**：不需要抓包逆向，直接用官方 CTP Python SDK 对接即可

---

## 用户账号信息（SimNow模拟账号）

| 字段 | 值 |
|---|---|
| 投资者代码（UserID） | 265221 |
| 经纪公司代码（BrokerID） | 9999 |
| 密码 | **让用户自己填写，不要硬编码** |
| 挂靠会员 | 华泰期货 |

**SimNow 行情服务器地址（二选一）：**
- 电信：`tcp://180.168.146.187:10211`
- 联通：`tcp://218.202.237.33:10211`

> SimNow 是上期技术官方提供的免费模拟环境，行情数据是真实的，下单是模拟的。交易时段才有数据推送（工作日 09:00-15:00 及夜盘）。

---

## 开发目标

1. 连接 SimNow 行情服务器
2. 订阅指定股指期货合约（如 IF、IC、IM、IH）
3. 实时接收 Tick 数据
4. 将数据存入本地 SQLite 数据库
5. 程序可以稳定长时间运行，断线自动重连

---

## 开发步骤（Claude按顺序执行）

### 第一步：确认Python环境

让用户在命令行运行：
```bash
python --version
pip --version
```
确认 Python 版本 >= 3.8。

---

### 第二步：安装依赖

```bash
pip install openctp-ctp
```

> `openctp-ctp` 是对上期技术官方 CTP API 的 Python 封装，免费开源。  
> 如果安装失败，备用命令：`pip install openctp-ctp -i https://pypi.tuna.tsinghua.edu.cn/simple`

---

### 第三步：编写行情订阅程序

**文件名**：`market_data.py`

程序需要包含以下功能：

**3.1 数据库初始化**
- 使用 SQLite（无需安装服务，文件即数据库）
- 数据库文件名：`market_data.db`
- 表名：`tick_data`
- 字段：
  - `id`：自增主键
  - `recv_time`：本地接收时间（TEXT，格式 `YYYY-MM-DD HH:MM:SS`）
  - `instrument_id`：合约代码（TEXT，如 `IF2506`）
  - `last_price`：最新价（REAL）
  - `open_price`：开盘价（REAL）
  - `highest_price`：最高价（REAL）
  - `lowest_price`：最低价（REAL）
  - `volume`：成交量（INTEGER）
  - `open_interest`：持仓量（REAL）
  - `bid_price1`：买一价（REAL）
  - `ask_price1`：卖一价（REAL）
  - `update_time`：交易所时间（TEXT）

**3.2 CTP 行情连接**
- 继承 `mdapi.CThostFtdcMdSpi`
- 实现以下回调：
  - `OnFrontConnected`：连接成功后自动登录
  - `OnRspUserLogin`：登录成功后订阅合约
  - `OnRtnDepthMarketData`：收到行情时存入数据库并打印到控制台
  - `OnFrontDisconnected`：断线时打印提示（CTP会自动重连）

**3.3 订阅合约**
- 默认订阅：`["IF2506", "IC2506", "IM2506", "IH2506"]`
- 合约代码让用户可以在文件顶部自行修改

**3.4 账号配置**
- 在文件顶部用常量定义，方便用户修改：
```python
USERID = "265221"
PASSWORD = "在这里填你的密码"
BROKERID = "9999"
MD_SERVER = "tcp://180.168.146.187:10211"
INSTRUMENTS = ["IF2506", "IC2506", "IM2506", "IH2506"]
```

---

### 第四步：验证程序运行

让用户运行：
```bash
python market_data.py
```

**预期输出（成功）**：
```
连接成功，正在登录...
登录成功，开始订阅行情...
订阅成功：IF2506
2026-05-27 09:30:01 | IF2506 | 价格: 3856.2 | 成交量: 1234
2026-05-27 09:30:02 | IF2506 | 价格: 3856.4 | 成交量: 1235
...
```

**常见错误处理**：

| 错误信息 | 原因 | 解决方法 |
|---|---|---|
| `连接超时` | 网络问题或非交易时段 | 检查网络，或等交易时段再试 |
| `登录失败 -3` | 密码错误 | 检查密码 |
| `没有数据推送` | 非交易时段 | SimNow 只在交易时段推送数据 |
| `ModuleNotFoundError` | 库未安装 | 重新 pip install |

---

### 第五步：查询验证数据已存入数据库

编写一个简单的查询脚本 `check_data.py`：
- 查询 `tick_data` 表最新10条记录
- 打印到控制台，格式清晰

---

### 第六步（可选）：定时抓取模式

如果用户需要的不是实时推送，而是每隔固定时间抓一次快照：
- 在 `OnRtnDepthMarketData` 回调里加时间间隔控制
- 用字典记录每个合约上次存储时间
- 只有距上次存储超过 N 秒才写入数据库

---

## 注意事项（Claude需要告知用户）

1. **交易时段**：SimNow 只在交易时段推送行情。工作日 09:00-11:30、13:00-15:00，夜盘视品种而定。非交易时段程序能连上但没有数据。

2. **合约代码格式**：股指期货合约代码格式为 `品种+年份月份`，如 `IF2506` 表示2025年6月的沪深300股指期货。每个季度换月，用户需要自行更新合约代码。

3. **主力合约查询**：不确定当前主力合约代码时，可以去中金所官网（cffex.com.cn）查询当前上市合约。

4. **数据库文件**：`market_data.db` 会在程序运行目录下自动生成，可以用 DB Browser for SQLite（免费软件）打开查看数据。

5. **长期运行**：如果需要长期运行，建议用 `pm2` 或 Windows 任务计划程序保持后台运行。

---

## 技术栈总结

| 组件 | 选型 | 说明 |
|---|---|---|
| 语言 | Python 3.8+ | |
| CTP接口 | openctp-ctp | 官方CTP的Python封装 |
| 数据库 | SQLite | 轻量，无需安装 |
| 数据访问 | sqlite3 | Python内置，无需额外安装 |

---

## 完成标准

以下条件全部满足，即为开发完成：

- [ ] `python market_data.py` 能正常启动，无报错
- [ ] 交易时段能看到实时价格输出
- [ ] `market_data.db` 文件存在，且 `tick_data` 表有数据
- [ ] `check_data.py` 能查询并打印最新数据
- [ ] 程序断线后能自动重连（CTP自带，无需额外处理）
