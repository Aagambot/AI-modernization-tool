import mlflow
import os
from datetime import datetime

class PipelineLogger:
    def __init__(self):
        # Set the remote tracking URI from .env
        self.tracking_uri = os.getenv("MLFLOW_TRACKING_URI")
        if self.tracking_uri:
            mlflow.set_tracking_uri(self.tracking_uri)
        
        mlflow.set_experiment("AI-Modernization-Evaluation")

    def log_run(self, config, metrics, artifact_paths):
        """
        Updated to accept three arguments: config, metrics, and artifact_paths.
        """
        with mlflow.start_run():
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
            scripts = [
                "main.py", "chat.py", "utils/logger.py", "engine/chunker.py",
                "core/graph_builder.py", "core/scanner.py", "data/storage.py", 
                "engine/embedder.py","engine/utils.py ", "core/parser.py" , "tests/verify_retrieval.py" ,"utils/graph_to_mermaid.py" ,"evaluation_report.json","golden_dataset.json"
            ]
            for script in scripts:
                if os.path.exists(script):
                    mlflow.log_artifact(script, "source_code")

            print(f"✅ MLflow Run Logged:")
