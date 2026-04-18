#!/usr/bin/env python3
"""
indicators.py — 技術指標計算模組
計算 RSI(14), MACD(12/26/9), MA(20/60) from yfinance history
"""

import yfinance as yf
import warnings
import pandas as pd

warnings.filterwarnings("ignore")


def fetch_ohlcv(sym: str, period: str = "6mo") -> pd.DataFrame:
    """抓取日 K 線資料"""
    tk = yf.Ticker(sym)
    hist = tk.history(period=period)
    return hist


def calc_rsi(close: pd.Series, period: int = 14) -> float:
    """計算最新 RSI"""
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return round(float(rsi.iloc[-1]), 1)


def calc_macd(close: pd.Series,
              fast: int = 12, slow: int = 26, signal: int = 9
              ) -> dict:
    """計算最新 MACD 值"""
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist_val = macd_line - signal_line
    return {
        "macd":   round(float(macd_line.iloc[-1]), 3),
        "signal": round(float(signal_line.iloc[-1]), 3),
        "hist":   round(float(hist_val.iloc[-1]), 3),
    }


def calc_ma(close: pd.Series, windows: list[int] = [20, 60]) -> dict:
    """計算各 MA 值及最新收盤與 MA 的距離 %"""
    result = {}
    price = float(close.iloc[-1])
    for w in windows:
        if len(close) >= w:
            ma_val = float(close.rolling(w).mean().iloc[-1])
            diff_pct = (price - ma_val) / ma_val * 100
            result[f"ma{w}"] = round(ma_val, 2)
            result[f"ma{w}_diff_pct"] = round(diff_pct, 1)
        else:
            result[f"ma{w}"] = None
            result[f"ma{w}_diff_pct"] = None
    return result


def get_indicators(sym: str) -> dict:
    """取得單一標的完整技術指標，回傳 dict"""
    try:
        hist = fetch_ohlcv(sym, period="6mo")
        if hist.empty or len(hist) < 30:
            return {"sym": sym, "error": "資料不足"}
        close = hist["Close"]
        rsi = calc_rsi(close)
        macd = calc_macd(close)
        ma = calc_ma(close, [20, 60])

        # 趨勢判斷
        trend = "N/A"
        if ma.get("ma20") and ma.get("ma60"):
            if ma["ma20_diff_pct"] > 0 and ma["ma60_diff_pct"] > 0:
                trend = "強勢（站上雙均線）"
            elif ma["ma20_diff_pct"] < 0 and ma["ma60_diff_pct"] < 0:
                trend = "弱勢（跌破雙均線）"
            elif ma["ma20_diff_pct"] > 0:
                trend = "短多（站上MA20）"
            else:
                trend = "短弱（跌破MA20）"

        # RSI 解讀
        if rsi >= 70:
            rsi_label = "超買"
        elif rsi <= 30:
            rsi_label = "超賣"
        elif rsi >= 55:
            rsi_label = "偏強"
        elif rsi <= 45:
            rsi_label = "偏弱"
        else:
            rsi_label = "中性"

        # MACD 方向
        macd_dir = "金叉↑" if macd["hist"] > 0 else "死叉↓"

        return {
            "sym":          sym,
            "rsi14":        rsi,
            "rsi_label":    rsi_label,
            "macd":         macd["macd"],
            "macd_signal":  macd["signal"],
            "macd_hist":    macd["hist"],
            "macd_dir":     macd_dir,
            "ma20":         ma.get("ma20"),
            "ma60":         ma.get("ma60"),
            "ma20_diff":    ma.get("ma20_diff_pct"),
            "ma60_diff":    ma.get("ma60_diff_pct"),
            "trend":        trend,
        }
    except Exception as e:
        return {"sym": sym, "error": str(e)[:60]}


if __name__ == "__main__":
    from fetch_prices import WATCHLIST
    print("\n技術指標快照")
    print("=" * 75)
    print(f"{'代碼':<12} {'RSI14':>7} {'RSI狀態':<8} {'MACD方向':<10} {'MA20偏離':>8} {'MA60偏離':>8} {'趨勢'}")
    print("-" * 75)
    for sym in WATCHLIST:
        ind = get_indicators(sym)
        if "error" in ind:
            print(f"{sym:<12} ERROR: {ind['error']}")
            continue
        ma20d = f"{ind['ma20_diff']:+.1f}%" if ind["ma20_diff"] is not None else "N/A"
        ma60d = f"{ind['ma60_diff']:+.1f}%" if ind["ma60_diff"] is not None else "N/A"
        print(f"{sym:<12} {ind['rsi14']:>7} {ind['rsi_label']:<8} {ind['macd_dir']:<10} {ma20d:>8} {ma60d:>8} {ind['trend']}")
    print("=" * 75)
