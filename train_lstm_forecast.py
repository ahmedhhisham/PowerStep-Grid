import pandas as pd, numpy as np, joblib
from sklearn.preprocessing import MinMaxScaler
import tensorflow as tf
from keras.models import Sequential
from keras.layers import LSTM, Dense, Dropout
from keras.callbacks import EarlyStopping

df = pd.read_parquet("data_energy_clean.parquet")
series = df.groupby(pd.Grouper(key="ts", freq="1min"))["power_mw"].sum().fillna(0).values.reshape(-1, 1)

scaler = MinMaxScaler()
scaled = scaler.fit_transform(series)

LOOKBACK = 30
def make_sequences(data, lookback):
    X, y = [], []
    for i in range(lookback, len(data)):
        X.append(data[i-lookback:i, 0])
        y.append(data[i, 0])
    return np.array(X), np.array(y)

X, y = make_sequences(scaled, LOOKBACK)
X = X.reshape((X.shape[0], X.shape[1], 1))

# تقسيم زمني (بدون خلط عشوائي - مهم جدًا للسلاسل الزمنية)
split = int(len(X) * 0.8)
X_train, X_test = X[:split], X[split:]
y_train, y_test = y[:split], y[split:]

model = Sequential([
    LSTM(64, activation="tanh", input_shape=(LOOKBACK, 1), return_sequences=False),
    Dropout(0.2),
    Dense(32, activation="relu"),
    Dense(1)
])
model.compile(optimizer="adam", loss="mse", metrics=["mae"])

es = EarlyStopping(monitor="val_loss", patience=5, restore_best_weights=True)
model.fit(X_train, y_train, validation_data=(X_test, y_test), epochs=50, batch_size=16, callbacks=[es])

model.save("models/energy_forecast_lstm.keras")
joblib.dump(scaler, "models/energy_scaler.joblib")
print("تم حفظ نموذج التنبؤ بالطاقة")