import os
import joblib
from xgboost import XGBClassifier

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARTIFACTS_DIR = os.path.join(BASE_DIR, "artifacts")

model = XGBClassifier()
model.load_model(os.path.join(ARTIFACTS_DIR, "xgb_model_final_2.json"))

preprocessor = joblib.load(os.path.join(ARTIFACTS_DIR, "preprocessor_final_2.pkl"))
selected_features = joblib.load(os.path.join(ARTIFACTS_DIR, "selected_features_2.pkl"))
threshold = joblib.load(os.path.join(ARTIFACTS_DIR, "threshold_2.pkl"))