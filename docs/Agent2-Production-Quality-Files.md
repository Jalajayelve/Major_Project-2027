# Agent 2 production quality files

These artifacts correspond to the most accurate reported Agent 2 production
model: the tuned `GradientBoostingClassifier` evaluated on the 3,198-row final
test split.

- [Accuracy-maximizing confusion matrix](../reports/agent2-quality/production-gradientboosting/confusion_matrix_accuracy_max_050.png)
- [Validation-selected comparison matrix](../reports/agent2-quality/production-gradientboosting/confusion_matrix_validation_selected_044.png)
- [Metrics JSON](../reports/agent2-quality/production-gradientboosting/metrics.json)
- [Classification report](../reports/agent2-quality/production-gradientboosting/classification_report.txt)

## Accuracy-maximizing result

At the default cutoff of **0.50**, the model reports:

- Accuracy: **88.43%**
- F1: **0.8038**
- Precision: **0.9404**
- Recall: **0.7019**
- ROC-AUC: **0.9340**
- Brier score: **0.0830**

Confusion matrix, with rows as observed labels and columns as predicted labels:

```text
                  Not admitted  Admitted
Not admitted             2070        48
Admitted                  322       758
```

The 0.44 validation-selected cutoff is included for comparison because it
raises recall to 73.80%, but its accuracy is lower at 87.77%. The earlier
requested 0.42 cutoff is not the selected threshold reported by the Agent 2
production notebook.

Regenerate the files from the repository root:

```powershell
python notebooks/generate_agent2_production_quality_files.py
```
