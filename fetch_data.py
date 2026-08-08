import sqlite3, pandas as pd

DB_PATH = "energy_system.db"

def get_energy(start=None, end=None):
    conn = sqlite3.connect(DB_PATH)
    q = "SELECT * FROM readings_energy"
    if start and end:
        q += f" WHERE ts BETWEEN '{start}' AND '{end}'"
    df = pd.read_sql(q, conn, parse_dates=["ts"])
    conn.close()
    return df

def get_rssi(start=None, end=None):
    conn = sqlite3.connect(DB_PATH)
    q = "SELECT * FROM readings_rssi"
    if start and end:
        q += f" WHERE ts BETWEEN '{start}' AND '{end}'"
    df = pd.read_sql(q, conn, parse_dates=["ts"])
    conn.close()
    return df

def export_training_parquet():
    get_energy().to_parquet("data_energy_raw.parquet")
    get_rssi().to_parquet("data_rssi_raw.parquet")
    print("تم تصدير ملفات parquet بنجاح")

if __name__ == "__main__":
    export_training_parquet()