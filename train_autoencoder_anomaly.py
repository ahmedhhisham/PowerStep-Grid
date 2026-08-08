import pandas as pd, numpy as np, json, joblib
from sklearn.preprocessing import StandardScaler
from keras.models import Model
from keras.layers import Input, Dense

# بيانات "طبيعية" فقط (من فترة تشغيل سليمة معروفة)
df = pd.read_parquet("data_energy_clean.parquet")
normal = df.pivot_table(index="ts", columns="tile_id", values="power_mw").fillna(method="ffill").dropna()

scaler = StandardScaler()
X = scaler.fit_transform(normal.values)

input_dim = X.shape[1]
inp = Input(shape=(input_dim,))
encoded = Dense(max(2, input_dim // 2), activation="relu")(inp)
decoded = Dense(input_dim, activation="linear")(encoded)
autoencoder = Model(inp, decoded)
autoencoder.compile(optimizer="adam", loss="mse")
autoencoder.fit(X, X, epochs=100, batch_size=16, validation_split=0.1, verbose=0)

recon = autoencoder.predict(X)
errors = np.mean(np.square(X - recon), axis=1)
threshold = float(np.mean(errors) + 3 * np.std(errors))

autoencoder.save("models/tile_anomaly_autoencoder.keras")
joblib.dump(scaler, "models/anomaly_scaler.joblib")
json.dump({"threshold": threshold, "columns": list(normal.columns)}, open("models/anomaly_config.json", "w"))
print(f"تم حفظ نموذج كشف الشذوذ | الحد الفاصل: {threshold:.4f}")