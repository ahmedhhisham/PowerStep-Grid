import pandas as pd, joblib
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from sklearn.metrics import classification_report, confusion_matrix
import matplotlib.pyplot as plt
import seaborn as sns

df = pd.read_parquet("features_rssi_labeled.parquet")
X = df[["mean", "std", "min", "max", "range", "mean_abs_diff"]]
y = df["label"]

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)

# --- Random Forest ---
rf = RandomForestClassifier(random_state=42)
rf_grid = GridSearchCV(rf, {"n_estimators": [100, 200], "max_depth": [5, 10, None]}, cv=5)
rf_grid.fit(X_train, y_train)

# --- SVM (مع تحجيم البيانات إجباري) ---
svm_pipe = Pipeline([("scaler", StandardScaler()), ("svc", SVC(kernel="rbf"))])
svm_grid = GridSearchCV(svm_pipe, {"svc__C": [1, 10, 100], "svc__gamma": ["scale", "auto"]}, cv=5)
svm_grid.fit(X_train, y_train)

for name, model in [("RandomForest", rf_grid.best_estimator_), ("SVM", svm_grid.best_estimator_)]:
    preds = model.predict(X_test)
    print(f"\n=== {name} ===")
    print(classification_report(y_test, preds))
    cm = confusion_matrix(y_test, preds, labels=model.classes_)
    sns.heatmap(cm, annot=True, fmt="d", xticklabels=model.classes_, yticklabels=model.classes_)
    plt.title(f"Confusion Matrix - {name}")
    plt.savefig(f"confusion_matrix_{name}.png")
    plt.clf()

best_model = rf_grid.best_estimator_ if rf_grid.best_score_ >= svm_grid.best_score_ else svm_grid.best_estimator_
joblib.dump(best_model, "models/occupancy_classifier.joblib")
print("تم حفظ أفضل نموذج")