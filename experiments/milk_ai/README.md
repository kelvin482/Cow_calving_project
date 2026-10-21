# Isolated milk AI experiments

This workspace is for testing anomaly-detection and milk-yield forecasting ideas before proposing any change to the Django application.

## Isolation rules

- Keep experiment code and Python packages out of the application's runtime and `requirements.txt`.
- Create a dedicated virtual environment inside this folder when an experiment is approved; `.venv/` is ignored here.
- Do not import Django application modules or write to its database from an experiment.
- Do not commit datasets, model weights, predictions, or reports containing farm or animal information. These local artifacts are ignored by this folder's `.gitignore`.
- Begin with clearly labeled synthetic data. Do not use real farm data or send data to an external model/service until the data handling is reviewed and approved.
- Record the model/version, input fields, data source, evaluation dates, metrics, and limitations for each experiment.
- A successful prototype is evidence for review, not approval to integrate it. Integration remains a separate roadmap task.

## Suggested experiment layout

- `src/`: isolated scripts and model adapters.
- `data/`: local-only input data; never commit it.
- `reports/`: local-only outputs; never commit them.
- `requirements.txt`: experiment-only, pinned dependencies, added when a specific experiment is selected.

The repository roadmap remains authoritative. The current next step is collecting and reviewing real daily milk records; creating this folder does not start the anomaly-detection stage.
