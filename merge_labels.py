import pandas as pd

def merge_labels(features_df, labels_path="labels.csv"):
    labels = pd.read_csv(labels_path, parse_dates=["start_ts", "end_ts"])
    features_df["label"] = None
    for _, row in labels.iterrows():
        mask = (features_df["ts"] >= row.start_ts) & (features_df["ts"] < row.end_ts)
        features_df.loc[mask, "label"] = row.label
    return features_df.dropna(subset=["label"])