import json
import time
import os
# Use flat imports to match your restored root directory structure
from storage import VectorStore  
from embedder import BGEEmbedder 

class RetrievalEvaluator:
    """
    OOP-based evaluator to provide metrics for the MLflow logger in main.py.
    """
    def __init__(self):
        self.store = VectorStore()
        self.embedder = BGEEmbedder()
        self.reset_metrics()

    def reset_metrics(self):
        self.results = []
        self.hits_at_5 = 0
        self.reciprocal_ranks = []

    def _normalize_path(self, path):
        return path.replace('\\', '/').lower()

    def evaluate_query(self, query, expected_file, k=5):
        start_time = time.time()
        query_vector = self.embedder.embed_batch([query])[0]
        table = self.store.get_table()
        
        if not table:
            # Friendly error if main.py hasn't been run yet
            return {"error": "Table not found"}

        search_results = table.search(query_vector).limit(k).to_list()
        latency = (time.time() - start_time) * 1000

        rank = 0
        found = False
        expected_path = self._normalize_path(expected_file)

        for i, res in enumerate(search_results):
            actual_path = self._normalize_path(res.get('file_path', ''))
            if expected_path in actual_path:
                rank = i + 1
                found = True
                break
        
        if found:
            self.hits_at_5 += 1
            self.reciprocal_ranks.append(1.0 / rank)
        else:
            self.reciprocal_ranks.append(0.0)

        return {
            "query": query,
            "found": found,
            "rank": rank if found else "N/A",
            "latency_ms": latency
        }

    def run_benchmark(self, dataset_path="golden_dataset.json"):
        """
        Main entry point for main.py. 
        Returns the dictionary needed for PipelineLogger.log_run().
        """
        self.reset_metrics()
        
        if not os.path.exists(dataset_path):
            print(f"❌ Dataset not found: {dataset_path}")
            return {"hit_rate": 0, "mrr": 0}

        with open(dataset_path, 'r') as f:
            golden_queries = json.load(f)

        for item in golden_queries:
            res = self.evaluate_query(item['query'], item['expected_file'])
            if "error" in res:
                print("❌ Critical Error: Table not found. Run main.py first.")
                return {"hit_rate": 0, "mrr": 0}
            self.results.append(res)

        # Calculate final values for the logger
        total = len(golden_queries)
        final_hit_rate = (self.hits_at_5 / total) * 100
        final_mrr = sum(self.reciprocal_ranks) / total

        return {
            "hit_rate": final_hit_rate,
            "mrr": final_mrr,
            "detailed_results": self.results
        }

if __name__ == "__main__":
    evaluator = RetrievalEvaluator()
    report = evaluator.run_benchmark()
    print(f"📊 Hit Rate @ 5: {report['hit_rate']:.2f}%")
    print(f"🏆 MRR: {report['mrr']:.3f}")