"""Compare zero-shot Chronos-2 forecasts with simple baselines on synthetic data."""

from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd


WORKSPACE = Path(__file__).resolve().parents[1]
REPORT_DIR = WORKSPACE / "reports"
MODEL_ID = "amazon/chronos-2"

# Keep downloaded weights and Hugging Face metadata inside this ignored workspace.
os.environ.setdefault("HF_HOME", str(WORKSPACE / ".cache" / "huggingface"))


def make_synthetic_milk_histories(
    *, cow_count: int = 8, day_count: int = 150, seed: int = 42
) -> pd.DataFrame:
    """Create deterministic, illustrative daily yields; these are not farm records."""
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2025-01-01", periods=day_count, freq="D")
    rows = []

    for cow_index in range(cow_count):
        initial_yield = rng.uniform(12.0, 18.0)
        rise = rng.uniform(5.0, 9.0)
        rise_days = rng.uniform(12.0, 24.0)
        peak_day = rng.uniform(35.0, 55.0)
        daily_decline = rng.uniform(0.025, 0.055)
        noise = rng.normal(0.0, 0.45, size=day_count)

        for day_index, record_date in enumerate(dates):
            rise_curve = rise * (1 - np.exp(-day_index / rise_days))
            decline_curve = daily_decline * max(day_index - peak_day, 0)
            yield_liters = max(
                0.0,
                initial_yield + rise_curve - decline_curve + noise[day_index],
            )
            rows.append(
                {
                    "cow_id": f"synthetic-cow-{cow_index + 1:02d}",
                    "timestamp": record_date,
                    "target": round(float(yield_liters), 2),
                }
            )

    return pd.DataFrame(rows)


def build_next_day_evaluation(
    histories: pd.DataFrame, *, context_days: int = 90, test_days: int = 5
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build separate context windows so no evaluation day enters its own history."""
    history_by_cow = {
        cow_id: cow_rows.sort_values("timestamp").reset_index(drop=True)
        for cow_id, cow_rows in histories.groupby("cow_id", sort=True)
    }
    context_rows = []
    expected_rows = []

    for cow_id, cow_rows in history_by_cow.items():
        first_test_index = len(cow_rows) - test_days
        for target_index in range(first_test_index, len(cow_rows)):
            context_start = max(0, target_index - context_days)
            context = cow_rows.iloc[context_start:target_index]
            if context.empty:
                raise ValueError(f"No history is available before {cow_id}'s test date.")

            # A unique item per forecast origin prevents later observations leaking
            # into an earlier forecast for the same synthetic cow.
            item_id = f"{cow_id}-origin-{target_index}"
            for row in context.itertuples(index=False):
                context_rows.append(
                    {
                        "item_id": item_id,
                        "timestamp": row.timestamp,
                        "target": row.target,
                    }
                )

            expected_rows.append(
                {
                    "item_id": item_id,
                    "timestamp": cow_rows.iloc[target_index]["timestamp"],
                    "actual": float(cow_rows.iloc[target_index]["target"]),
                    "last_day": float(context.iloc[-1]["target"]),
                    "last_7_day_mean": float(context.tail(7)["target"].mean()),
                }
            )

    return pd.DataFrame(context_rows), pd.DataFrame(expected_rows)


def calculate_metrics(actual: np.ndarray, predicted: np.ndarray) -> dict[str, float]:
    errors = predicted - actual
    return {
        "mae_liters": float(np.mean(np.abs(errors))),
        "rmse_liters": float(np.sqrt(np.mean(errors**2))),
    }


def main() -> None:
    # Imported after HF_HOME is set so model files stay inside the experiment folder.
    from chronos import Chronos2Pipeline

    histories = make_synthetic_milk_histories()
    context_df, expected_df = build_next_day_evaluation(histories)
    print(
        f"Synthetic-only run: {histories['cow_id'].nunique()} cows, "
        f"{len(expected_df)} one-day forecasts, {len(context_df)} context rows."
    )
    print(f"Loading pretrained {MODEL_ID} on CPU; first run downloads model weights.")

    pipeline = Chronos2Pipeline.from_pretrained(MODEL_ID, device_map="cpu")
    predictions = pipeline.predict_df(
        context_df,
        prediction_length=1,
        quantile_levels=[0.1, 0.5, 0.9],
        id_column="item_id",
        timestamp_column="timestamp",
        target="target",
        freq="D",
    )[["item_id", "predictions"]]

    results = expected_df.merge(predictions, on="item_id", validate="one_to_one")
    if results.empty or not np.isfinite(results["predictions"]).all():
        raise RuntimeError("Chronos-2 did not return finite predictions for all cases.")

    metric_summary = {
        "data_kind": "synthetic; not evidence of farm accuracy",
        "model_id": MODEL_ID,
        "forecast_horizon_days": 1,
        "cow_count": int(histories["cow_id"].nunique()),
        "forecast_count": int(len(results)),
        "metrics": {
            "chronos_2": calculate_metrics(
                results["actual"].to_numpy(), results["predictions"].to_numpy()
            ),
            "last_day_baseline": calculate_metrics(
                results["actual"].to_numpy(), results["last_day"].to_numpy()
            ),
            "last_7_day_mean_baseline": calculate_metrics(
                results["actual"].to_numpy(), results["last_7_day_mean"].to_numpy()
            ),
        },
    }

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "chronos_smoke_summary.json").write_text(
        json.dumps(metric_summary, indent=2) + "\n", encoding="utf-8"
    )
    results.to_csv(REPORT_DIR / "chronos_smoke_predictions.csv", index=False)
    print(json.dumps(metric_summary, indent=2))
    print(f"Local-only reports saved under: {REPORT_DIR}")


if __name__ == "__main__":
    main()
