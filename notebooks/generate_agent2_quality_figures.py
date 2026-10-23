"""Generate report figures from Agent 2 grouped out-of-fold predictions."""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.calibration import calibration_curve
from sklearn.metrics import ConfusionMatrixDisplay, confusion_matrix


ROOT = Path(__file__).resolve().parents[1]
PREDICTIONS = ROOT / "data" / "processed" / "agent2" / "oof_predictions.csv"
OUT = ROOT / "reports" / "agent2-quality"
THRESHOLD = 0.42


def load_predictions() -> pd.DataFrame:
    if not PREDICTIONS.exists():
        raise FileNotFoundError(
            f"Missing {PREDICTIONS}. Run the Agent 2 grouped-CV pipeline first."
        )
    frame = pd.read_csv(PREDICTIONS)
    required = {"y", "with_profile_strength"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Agent 2 predictions are missing columns: {sorted(missing)}")
    if not frame["y"].isin([0, 1]).all():
        raise ValueError("Agent 2 labels must be binary.")
    if not frame["with_profile_strength"].between(0, 1).all():
        raise ValueError("Agent 2 probabilities must be between 0 and 1.")
    return frame


def save_reliability_plot(frame: pd.DataFrame) -> None:
    observed, predicted = calibration_curve(
        frame["y"], frame["with_profile_strength"], n_bins=10, strategy="uniform"
    )
    counts = pd.cut(
        frame["with_profile_strength"],
        bins=np.linspace(0, 1, 11),
        include_lowest=True,
    ).value_counts(sort=False)

    fig, ax = plt.subplots(figsize=(7.2, 5.2), dpi=180)
    ax.plot([0, 1], [0, 1], "--", color="#6b7280", label="Perfect calibration")
    ax.plot(
        predicted,
        observed,
        "o-",
        color="#1f77b4",
        linewidth=2,
        markersize=5,
        label="Agent 2 grouped OOF",
    )
    for x, y, count in zip(predicted, observed, counts[counts > 0]):
        ax.annotate(
            str(count),
            (x, y),
            textcoords="offset points",
            xytext=(0, 7),
            ha="center",
            fontsize=8,
        )
    ax.set(
        xlim=(0, 1),
        ylim=(0, 1),
        xlabel="Mean predicted admission probability",
        ylabel="Observed admission frequency",
        title="Agent 2 reliability diagram",
    )
    ax.grid(alpha=0.25)
    ax.legend(loc="upper left")
    fig.text(
        0.5,
        0.01,
        "Five-fold GroupKFold by applicant_id; labels and priors are unverified",
        ha="center",
        fontsize=8,
    )
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(OUT / "agent2_reliability_diagram.png", bbox_inches="tight")
    plt.close(fig)


def save_confusion_matrix(frame: pd.DataFrame) -> None:
    actual = frame["y"].astype(int)
    predicted = (frame["with_profile_strength"] >= THRESHOLD).astype(int)
    matrix = confusion_matrix(actual, predicted, labels=[0, 1])

    fig, ax = plt.subplots(figsize=(5.8, 5.1), dpi=180)
    ConfusionMatrixDisplay(
        confusion_matrix=matrix,
        display_labels=["Not admitted", "Admitted"],
    ).plot(
        ax=ax,
        cmap="Blues",
        values_format="d",
        colorbar=False,
    )
    ax.set(
        title=f"Agent 2 confusion matrix (cutoff = {THRESHOLD:.2f})",
        xlabel="Predicted label",
        ylabel="Observed label",
    )
    fig.text(
        0.5,
        0.01,
        "Pooled grouped out-of-fold rows; not an independent external test set",
        ha="center",
        fontsize=8,
    )
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(OUT / "agent2_confusion_matrix_threshold_042.png", bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    frame = load_predictions()
    save_reliability_plot(frame)
    save_confusion_matrix(frame)
    print(f"Saved Agent 2 quality figures to {OUT}")


if __name__ == "__main__":
    main()
