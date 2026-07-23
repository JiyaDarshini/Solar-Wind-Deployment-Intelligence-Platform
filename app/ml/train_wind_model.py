"""
Trains the Wind Potential Prediction model (Module 6).

As with train_solar_model.py, this uses a physically-grounded synthetic
dataset (wind speed, air density proxy via elevation, turbulence,
hub height, rotor diameter -> capacity factor) so the pipeline can be
built and tested before a historical Global Wind Atlas / met-mast
dataset is wired in.

Run:
    python -m app.ml.train_wind_model
"""
import os

import joblib
import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split


def generate_training_dataset(n_samples: int = 8000, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    wind_speed = np.clip(rng.normal(6.5, 2.2, n_samples), 1.0, 14.0)
    elevation = np.clip(rng.exponential(300, n_samples), 0, 3000)
    turbulence_intensity = np.clip(rng.normal(14, 4, n_samples), 4, 30)
    hub_height = rng.uniform(60, 140, n_samples)
    rotor_diameter = rng.uniform(80, 160, n_samples)

    # Wind power density approx: 0.5 * rho * v^3 (air density derated slightly with elevation)
    air_density = 1.225 * np.exp(-elevation / 8500)
    power_density = 0.5 * air_density * wind_speed ** 3

    swept_area = np.pi * (rotor_diameter / 2) ** 2
    turbine_capacity_kw = 2500  # reference turbine class

    # Simplified capacity factor model: rises with power density & hub
    # height (wind shear), penalized by high turbulence.
    hub_shear_bonus = (hub_height - 60) / 80 * 6
    turbulence_penalty = np.clip(turbulence_intensity - 12, 0, None) * 0.4
    base_cf = (power_density / 12) * 3.2 + hub_shear_bonus - turbulence_penalty
    capacity_factor = np.clip(base_cf + rng.normal(0, 2, n_samples), 5, 55)

    return pd.DataFrame(
        {
            "wind_speed_ms": wind_speed,
            "elevation_m": elevation,
            "turbulence_intensity_pct": turbulence_intensity,
            "hub_height_m": hub_height,
            "rotor_diameter_m": rotor_diameter,
            "power_density_w_m2": power_density,
            "capacity_factor_pct": capacity_factor,
        }
    )


FEATURE_COLUMNS = [
    "wind_speed_ms",
    "elevation_m",
    "turbulence_intensity_pct",
    "hub_height_m",
    "rotor_diameter_m",
    "power_density_w_m2",
]
TARGET_COLUMN = "capacity_factor_pct"


def train_and_save(output_path: str = "app/ml/artifacts/wind_potential_model.joblib"):
    df = generate_training_dataset()
    X_train, X_test, y_train, y_test = train_test_split(
        df[FEATURE_COLUMNS], df[TARGET_COLUMN], test_size=0.2, random_state=42
    )

    candidates = {
        "lightgbm": LGBMRegressor(n_estimators=300, max_depth=6, learning_rate=0.05, random_state=42),
        "random_forest": RandomForestRegressor(n_estimators=300, max_depth=10, random_state=42),
    }

    best_model, best_name, best_mae = None, None, float("inf")
    for name, model in candidates.items():
        model.fit(X_train, y_train)
        preds = model.predict(X_test)
        mae = mean_absolute_error(y_test, preds)
        r2 = r2_score(y_test, preds)
        print(f"[wind] {name}: MAE={mae:.3f} R2={r2:.3f}")
        if mae < best_mae:
            best_model, best_name, best_mae = model, name, mae

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    joblib.dump({"model": best_model, "features": FEATURE_COLUMNS, "model_name": best_name}, output_path)
    print(f"Saved best wind model ({best_name}, MAE={best_mae:.3f}) -> {output_path}")


if __name__ == "__main__":
    train_and_save()
