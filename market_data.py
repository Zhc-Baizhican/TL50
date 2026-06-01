import sqlite3
from datetime import datetime

# ============================================================
# 用户配置区 —— 按需修改
# ============================================================
USERID      = "265221"
PASSWORD    = "在这里填你的密码"
BROKERID    = "9999"
APPID       = "simnow_client_test"
AUTHCODE    = "0000000000000000"
MD_SERVER   = "tcp://182.254.243.31:30011"
INSTRUMENTS = ["IF2506", "IC2506", "IM2506", "IH2506"]
DB_FILE     = "market_data.db"
# ============================================================

try:
    from openctp_ctp import mdapi
except ImportError:
    raise SystemExit("请先安装依赖：pip install openctp-ctp")


def init_db():
    conn = sqlite3.connect(DB_FILE)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tick_data (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            recv_time       TEXT,
            instrument_id   TEXT,
            last_price      REAL,
            open_price      REAL,
            highest_price   REAL,
            lowest_price    REAL,
            volume          INTEGER,
            open_interest   REAL,
            bid_price1      REAL,
            ask_price1      REAL,
            update_time     TEXT
        )
    """)
    conn.commit()
    conn.close()


class MarketDataSpi(mdapi.CThostFtdcMdSpi):

    def __init__(self, api):
        super().__init__()
        self.api = api
        self.conn = sqlite3.connect(DB_FILE, check_same_thread=False)

    def OnFrontConnected(self):
        print("连接成功，正在登录...")
        req = mdapi.CThostFtdcReqUserLoginField()
        req.BrokerID = BROKERID
        req.UserID   = USERID
        req.Password = PASSWORD
        self.api.ReqUserLogin(req, 0)

    def OnFrontDisconnected(self, nReason):
        print(f"连接断开（原因码 {nReason}），CTP 将自动重连...")

    def OnRspUserLogin(self, pRspUserLogin, pRspInfo, nRequestID, bIsLast):
        if pRspInfo and pRspInfo.ErrorID != 0:
            print(f"登录失败：{pRspInfo.ErrorID} {pRspInfo.ErrorMsg}")
            return
        print("登录成功，开始订阅行情...")
        instruments = [s.encode() for s in INSTRUMENTS]
        self.api.SubscribeMarketData(instruments, len(instruments))

    def OnRspSubMarketData(self, pSpecificInstrument, pRspInfo, nRequestID, bIsLast):
        if pRspInfo and pRspInfo.ErrorID != 0:
            print(f"订阅失败：{pRspInfo.ErrorMsg}")
        else:
            print(f"订阅成功：{pSpecificInstrument.InstrumentID}")

    def OnRtnDepthMarketData(self, pDepthMarketData):
        d = pDepthMarketData
        recv_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"{recv_time} | {d.InstrumentID} | 价格: {d.LastPrice} | 成交量: {d.Volume}")
        self.conn.execute("""
            INSERT INTO tick_data
              (recv_time, instrument_id, last_price, open_price, highest_price,
               lowest_price, volume, open_interest, bid_price1, ask_price1, update_time)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, (
            recv_time,
            d.InstrumentID,
            d.LastPrice,
            d.OpenPrice,
            d.HighestPrice,
            d.LowestPrice,
            d.Volume,
            d.OpenInterest,
            d.BidPrice1,
            d.AskPrice1,
            d.UpdateTime,
        ))
        self.conn.commit()


def main():
    init_db()
    api = mdapi.CThostFtdcMdApi.CreateFtdcMdApi("./md_flow/")
    spi = MarketDataSpi(api)
    api.RegisterSpi(spi)
    api.RegisterFront(MD_SERVER)
    api.Init()
    print("行情程序已启动，按 Ctrl+C 退出")
    try:
        api.Join()
    except KeyboardInterrupt:
        print("用户中断，退出。")
        api.Release()


if __name__ == "__main__":
    main()
