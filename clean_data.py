import pandas as pd
import numpy as np

def remove_outliers_iqr(df: pd.DataFrame, col: str) -> pd.DataFrame:
    q1, q3 = df[col].quantile(0.25), df[col].quantile(0.75)
    iqr = q3 - q1
    lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    return df[(df[col] >= lower) & (df[col] <= upper)]

def kalman_1d(series: pd.Series, process_var=1e-4, measurement_var=1.0) -> pd.Series:
    """فلتر كالمان بسيط لتنعيم تذبذب RSSI"""
    n = len(series)
    xhat = np.zeros(n); P = np.zeros(n)
    xhat[0] = series.iloc[0]; P[0] = 1.0
    for k in range(1, n):
        xhat_minus = xhat[k-1]
        P_minus = P[k-1] + process_var
        K = P_minus / (P_minus + measurement_var)
        xhat[k] = xhat_minus + K * (series.iloc[k] - xhat_minus)
        P[k] = (1 - K) * P_minus
    return pd.Series(xhat, index=series.index)

def clean_rssi(df: pd.DataFrame) -> pd.DataFrame:
    df = df.dropna(subset=["rssi"]).drop_duplicates(subset=["ts", "node_id"])
    df = remove_outliers_iqr(df, "rssi")
    df = df.sort_values("ts").set_index("ts")
    df = df.resample("1S").mean(numeric_only=True).interpolate(method="linear")
    df["rssi_smooth"] = kalman_1d(df["rssi"])
    return df.reset_index()

def clean_energy(df: pd.DataFrame) -> pd.DataFrame:
    df = df.dropna(subset=["power_mw"]).drop_duplicates(subset=["ts", "tile_id"])
    df = remove_outliers_iqr(df, "power_mw")
    return df.sort_values("ts")

def build_feature_windows(df: pd.DataFrame, window="5S") -> pd.DataFrame:
    """هندسة خصائص من نافذة زمنية لتصنيف الإشغال"""
    df = df.set_index("ts")
    feats = df["rssi_smooth"].resample(window).agg(
        mean="mean", std="std", min="min", max="max",
        range=lambda x: x.max() - x.min() if len(x) else np.nan
    )
    feats["mean_abs_diff"] = df["rssi_smooth"].diff().abs().resample(window).mean()
    return feats.dropna().reset_index()

if __name__ == "__main__":
    raw = pd.read_parquet("data_rssi_raw.parquet")
    cleaned = clean_rssi(raw)
    features = build_feature_windows(cleaned)
    features.to_parquet("features_rssi_clean.parquet")
    print(f"تم تجهيز {len(features)} صف من الخصائص")