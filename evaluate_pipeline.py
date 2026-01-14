import json
import time
import numpy as np
from chat import ModernizationChat

class PipelineEvaluator:
    def __init__(self, chat_instance: ModernizationChat):
        self.chat = chat_instance
        self.results = {}

    def run_evaluation(self, expected_fields, expected_methods):
        """
        Calculates all 5 Success Metrics based on the latest Gemini output.
        """
        print("🧪 Starting Evaluation Pass...")
        
        # 1. Performance & Generation (Metric 5)
        start_time = time.time()
        model_json, r_lat, g_lat = self.chat.generate_domain_model()
        total_time = (time.time() - start_time) * 1000
        
        data = json.loads(model_json)
        
        # 2. Retrieval & Findability (Metric 1 & 3)
        found_fields = [f['name'] for f in data.get('fields', [])]
        field_precision = sum(1 for f in expected_fields if f in found_fields) / len(expected_fields)
        
        # 3. Workflow Traceability (Metric 4)
        found_methods = [m['name'] for m in data.get('methods', [])]
        method_recall = sum(1 for m in expected_methods if m in found_methods) / len(expected_methods)

        # Store Results
        self.results = {
            "p95_Retrieval_Latency_ms": r_lat,
            "Generation_Latency_ms": g_lat,
            "Context_Precision_Fields": field_precision,
            "Workflow_Recall_Methods": method_recall,
            "Logic_Findability_Score": 1.0 if len(data.get('business_rules', [])) > 0 else 0.0
        }
        
        return self.results

    def print_report(self):
        print("\n" + "="*50)
        print("📊 SENIOR'S KPI REPORT: SALES INVOICE PIPELINE")
        print("="*50)
        
        thresholds = {
            "p95_Retrieval_Latency_ms": 500.0, # Lower is better
            "Context_Precision_Fields": 0.75,
            "Workflow_Recall_Methods": 0.80,
            "Logic_Findability_Score": 1.0
        }

        for metric, value in self.results.items():
            status = "✅ PASS"
            if metric in thresholds:
                if metric == "p95_Retrieval_Latency_ms":
                    if value > thresholds[metric]: status = "❌ FAIL"
                elif value < thresholds[metric]: status = "❌ FAIL"
            
            print(f"{status} | {metric:<25} : {value:.4f}")
        print("="*50)

if __name__ == "__main__":
    # Initialize the high-performance chat
    chat = ModernizationChat()
    evaluator = PipelineEvaluator(chat)

    # Define 'Ground Truth' based on Sales Invoice Source
    target_fields = ["customer", "is_return", "grand_total", "posting_date"]
    target_methods = ["validate", "on_submit"]

    # Run and Report
    evaluator.run_evaluation(target_fields, target_methods)
    evaluator.print_report()