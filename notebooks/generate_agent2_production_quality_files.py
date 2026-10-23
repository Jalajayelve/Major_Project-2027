"""Create the Agent 2 production-model quality artifacts from notebook results."""

from pathlib import Path
import json

import matplotlib.pyplot as plt
import numpy as np
from sklearn.metrics import ConfusionMatrixDisplay


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "agent2-quality" / "production-gradientboosting"

# These values are the final test-set results emitted by
# AGENT2_University_agent.ipynb (cell 46), with 3,198 test rows.
DEFAULT_THRESHOLD = {
    "model": "GradientBoostingClassifier",
    "threshold": 0.50,
    "accuracy": 0.8843,
    "f1": 0.8038,
    "precision": 0.9404,
    "recall": 0.7019,
    "roc_auc": 0.9340,
    "brier": 0.0830,
    "confusion_matrix": [[2070, 48], [322, 758]],
    "support": {"not_admitted": 2118, "admitted": 1080},
    "evaluation_rows": 3198,
}

VALIDATION_THRESHOLD = {
    "model": "GradientBoostingClassifier",
    "threshold": 0.44,
    "accuracy": 0.8777,
    "f1": 0.8030,
    "precision": 0.8807,
    "recall": 0.7380,
    "roc_auc": 0.9340,
    "brier": 0.0830,
    "confusion_matrix": [[2010, 108], [283, 797]],
    "support": {"not_admitted": 2118, "admitted": 1080},
    "evaluation_rows": 3198,
}


def save_matrix(result: dict, filename: str, subtitle: str) -> None:
    fig, ax = plt.subplots(figsize=(6.2, 5.3), dpi=180)
    ConfusionMatrixDisplay(
        confusion_matrix=np.asarray(result["confusion_matrix"]),
        display_labels=["Not admitted", "Admitted"],
    ).plot(ax=ax, cmap="Blues", values_format="d", colorbar=False)
    ax.set(
        title=(
            f"Agent 2 production model\n"
            f"GradientBoostingClassifier (cutoff = {result['threshold']:.2f})"
        ),
        xlabel="Predicted label",
        ylabel="Observed label",
    )
    fig.text(0.5, 0.01, subtitle, ha="center", fontsize=8)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(OUT / filename, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "metrics.json").write_text(
        json.dumps(
            {
                "accuracy_maximizing_result": DEFAULT_THRESHOLD,
                "validation_selected_comparison": VALIDATION_THRESHOLD,
                "source": "backend/app/agents/university_matching_agent/AGENT2_University_agent.ipynb, cell 46",
                "note": (
                    "The 0.50 result is the most accurate reported production result. "
                    "The 0.44 result is retained for recall-oriented comparison."
                ),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (OUT / "classification_report.txt").write_text(
        """Agent 2 production model: GradientBoostingClassifier
Evaluation: final test split, 3,198 rows

Accuracy-maximizing cutoff: 0.50
Accuracy: 0.8843
F1: 0.8038
Precision: 0.9404
Recall: 0.7019
ROC-AUC: 0.9340
Brier: 0.0830

Confusion matrix (rows = observed, columns = predicted):
                  Not admitted  Admitted
Not admitted             2070        48
Admitted                  322       758

Comparison: validation-selected cutoff 0.44
Accuracy: 0.8777 | F1: 0.8030 | Precision: 0.8807 | Recall: 0.7380
Confusion matrix:
                  Not admitted  Admitted
Not admitted             2010       108
Admitted                  283       797
""",
        encoding="utf-8",
    )
    save_matrix(
        DEFAULT_THRESHOLD,
        "confusion_matrix_accuracy_max_050.png",
        "Final test split: 3,198 rows; accuracy = 88.43%",
    )
    save_matrix(
        VALIDATION_THRESHOLD,
        "confusion_matrix_validation_selected_044.png",
        "Final test split: 3,198 rows; validation-selected cutoff",
    )
    print(f"Saved production quality files to {OUT}")


if __name__ == "__main__":
    main()
