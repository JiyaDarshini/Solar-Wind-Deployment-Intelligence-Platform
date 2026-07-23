"""
Trains the Solar Potential Prediction model (Module 5).

Real deployments should replace `generate_training_dataset()` with a
loader that pulls historical NASA POWER irradiance + known plant
performance records. Until that historical dataset is wired up, this
script builds a physically-grounded synthetic dataset (irradiance,
temperature, cloud cover, slope, aspect, panel efficiency -> capacity
factor) so the rest of the pipeline (API, scoring, dashboards) can be
built and tested end-to-end now, then swapped to real data later without
changing any downstream code.

Run:
    python -m app.ml.train_solar_model
"""
import os

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
from xgboost import XGBRegressor


def generate_training_dataset(n_samples: int = 8000, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    latitude = rng.uniform(-60, 60, n_samples)
    irradiance = np.clip(6.5 - (np.abs(latitude) / 90) * 4.0 + rng.normal(0, 0.4, n_samples), 1.0, 8.5)
    temperature = 28 - np.abs(latitude) * 0.35 + rng.normal(0, 3, n_samples)
    cloud_cover = np.clip(rng.normal(35, 15, n_samples), 0, 100)
    slope = np.clip(rng.exponential(4, n_samples), 0, 45)
    aspect_penalty = rng.uniform(0, 1, n_samples)  # 0 = optimal south/north facing
    panel_efficiency = rng.uniform(15, 22, n_samples)

    # Physically-motivated capacity factor formula with noise, capped 0-40%
    base_cf = (
        (irradiance / 8.0) * 32
        - (cloud_cover / 100) * 6
        - (slope / 45) * 3
        - aspect_penalty * 4
        + (panel_efficiency - 18) * 0.6
        - np.clip((temperature - 25), 0, None) * 0.08  # heat derating above 25C
    )
    capacity_factor = np.clip(base_cf + rng.normal(0, 1.5, n_samples), 5, 35)

    return pd.DataFrame(
        {
            "irradiance_kwh_m2_day": irradiance,
            "temperature_c": temperature,
            "cloud_cover_pct": cloud_cover,
            "slope_degrees": slope,
            "aspect_penalty": aspect_penalty,
            "panel_efficiency_pct": panel_efficiency,
            "capacity_factor_pct": capacity_factor,
        }
    )


FEATURE_COLUMNS = [
    "irradiance_kwh_m2_day",
    "temperature_c",
    "cloud_cover_pct",
    "slope_degrees",
    "aspect_penalty",
    "panel_efficiency_pct",
]
TARGET_COLUMN = "capacity_factor_pct"


def train_and_save(output_path: str = "app/ml/artifacts/solar_potential_model.joblib"):
    df = generate_training_dataset()
    X_train, X_test, y_train, y_test = train_test_split(
        df[FEATURE_COLUMNS], df[TARGET_COLUMN], test_size=0.2, random_state=42
    )

    candidates = {
        "xgboost": XGBRegressor(
            n_estimators=300, max_depth=5, learning_rate=0.05, subsample=0.9, random_state=42
        ),
        "random_forest": RandomForestRegressor(n_estimators=300, max_depth=10, random_state=42),
    }

    best_model, best_name, best_mae = None, None, float("inf")
    for name, model in candidates.items():
        model.fit(X_train, y_train)
        preds = model.predict(X_test)
        mae = mean_absolute_error(y_test, preds)
        r2 = r2_score(y_test, preds)
        print(f"[solar] {name}: MAE={mae:.3f} R2={r2:.3f}")
        if mae < best_mae:
            best_model, best_name, best_mae = model, name, mae

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    joblib.dump({"model": best_model, "features": FEATURE_COLUMNS, "model_name": best_name}, output_path)
    print(f"Saved best solar model ({best_name}, MAE={best_mae:.3f}) -> {output_path}")


if __name__ == "__main__":
    train_and_save()
