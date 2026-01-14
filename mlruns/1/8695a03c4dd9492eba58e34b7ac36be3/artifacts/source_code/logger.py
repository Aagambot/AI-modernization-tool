import mlflow
import os
from datetime import datetime

class PipelineLogger:
    def __init__(self, experiment_name="ERP_Modernization"):
        mlflow.set_experiment(experiment_name)

    def log_run(self, config, metrics, artifact_paths):
        run_name = f"{config['entity']}_{datetime.now().strftime('%m%d_%H%M')}"
        with mlflow.start_run(run_name=run_name):
            # 1. Log Config/Params
            mlflow.log_params(config)

            # 2. Log Evaluation Metrics
            mlflow.log_metrics(metrics)

            # 3. Log Resulting Files (Database, Graph, JSON)
            for key, path in artifact_paths.items():
                if os.path.exists(path):
                    if os.path.isdir(path):
                        mlflow.log_artifact(path, f"data/{key}")
                    else:
                        mlflow.log_artifact(path, "data")

            # 4. Log the Pipeline Code itself for versioning
            scripts = ["main.py", "chat.py", "evaluate_pipeline.py", "logger.py", "chunker.py","parser.py","graph_builder.py", "scanner.py", "storage.py", "embedder.py"]
            for script in scripts:
                if os.path.exists(script):
                    mlflow.log_artifact(script, "source_code")

            print(f"✅ MLflow Run Logged: {run_name}")