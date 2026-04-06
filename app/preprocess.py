import pandas as pd
from app.model_loader import preprocessor


def prepare_dataframe(payload: dict) -> pd.DataFrame:
    df = pd.DataFrame([payload])

    for col in ["new_device", "location_mismatch"]:
        if col in df.columns:
            df.loc[:, col] = df.loc[:, col].astype(int)

    preproc_cols = []
    for transformer in preprocessor.transformers_:
        if len(transformer) >= 3:
            preproc_cols += list(transformer[2])

    for col in preproc_cols:
        if col not in df.columns:
            df[col] = 0

    return df[preproc_cols]


def transform_features(df: pd.DataFrame):
    return preprocessor.transform(df)