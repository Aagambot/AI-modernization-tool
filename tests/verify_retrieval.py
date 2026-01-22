import json
import time
import os
import asyncio
from data.storage import VectorStore  
from engine.embedder import BGEEmbedder 
from chat import ModernizationChat 
class RetrievalEvaluator:
    def __init__(self):
        self.store = VectorStore()
        self.embedder = BGEEmbedder()
        self.chat = ModernizationChat()
        self.reset_metrics()

    def reset_metrics(self):
        self.results = []
        self.hits_at_5 = 0
        self.reciprocal_ranks = []
        self.total_accuracy = 0
        self.total_completeness = 0

    def _normalize_path(self, path):
        return path.replace('\\', '/').lower()

    async def judge_response(self, query, generated_answer, expected_logic):
        """
        STEP 2: LLM-as-a-Judge logic.
        Grades the answer based on Accuracy and Completeness (1-5).
        """
        # The prompt defines the strict rubric for the judge
        prompt = f"""
        Act as a Senior ERPNext Architect. Grade the AI's response based on the 'Expected Logic'.
        
        USER QUERY: {query}
        EXPECTED LOGIC (Ground Truth): {expected_logic}
        AI GENERATED ANSWER: {generated_answer}
        
        GRADING RUBRIC (Scale 1-5):
        - Accuracy: Does it identify the correct functions/entry points? (5=Perfect, 1=Hallucinated)
        - Completeness: Does it cover execution phases (Validation/Accounting/Stock) and conditions? (5=Full, 1=Vague)
        
        Return ONLY a JSON object: {{"accuracy": <score>, "completeness": <score>, "rationale": "<1 sentence text>"}}
        """
        try:
            # Reusing your ModernizationChat LLM client to act as the judge
            raw_response = await self.chat.llm.generate_content_async(
                prompt, 
                generation_config={"response_mime_type": "application/json"}
            )
            return json.loads(raw_response.text)
        except Exception as e:
            print(f"⚠️ Judge Error: {e}")
            return {"accuracy": 0, "completeness": 0, "rationale": "Judge failed"}

    async def evaluate_query(self, item, k=5):
        """
        Combined Step 1 (Retrieval) and Step 2 (Judging).
        """
        query = item['query']
        expected_file = item['expected_file']
        expected_logic = item.get('expected_logic', "No ground truth provided.")

        # --- STEP 1: RETRIEVAL ---
        start_time = time.time()
        query_vector = self.embedder.embed_batch([query])[0]
        table = self.store.get_table()
        
        if not table:
            return {"error": "Table not found"}

        search_results = table.search(query_vector).limit(k).to_list()
        retrieval_latency = (time.time() - start_time) * 1000

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

        # --- STEP 2: GENERATION & JUDGING ---
        # Generate the answer using your tool's actual RAG pipeline
        # We assume the directory of the expected file as the target for context
        target_dir = os.path.dirname(expected_file)
        model_json, r_lat, g_lat = await self.chat.generate_domain_model(target_dir, query=query)
        
        # Grade the generated answer
        judge_scores = await self.judge_response(query, model_json, expected_logic)
        
        self.total_accuracy += judge_scores['accuracy']
        self.total_completeness += judge_scores['completeness']

        return {
            "query": query,
            "found": found,
            "rank": rank if found else "N/A",
            "retrieval_latency": retrieval_latency,
            "generation_latency": g_lat,
            "scores": judge_scores
        }

    async def run_benchmark(self, dataset_path="golden_dataset.json"):
        self.reset_metrics()
        
        if not os.path.exists(dataset_path):
            print(f"❌ Dataset not found: {dataset_path}")
            return {"hit_rate": 0, "mrr": 0}

        with open(dataset_path, 'r') as f:
            golden_queries = json.load(f)

        for item in golden_queries:
            res = await self.evaluate_query(item)
            if "error" in res:
                print("❌ Critical Error: Table not found. Run main.py first.")
                return {"hit_rate": 0, "mrr": 0}
            self.results.append(res)

        total = len(golden_queries)
        final_hit_rate = (self.hits_at_5 / total) * 100
        final_mrr = sum(self.reciprocal_ranks) / total
        avg_accuracy = self.total_accuracy / total
        avg_completeness = self.total_completeness / total

        return {
            "hit_rate": final_hit_rate,
            "mrr": final_mrr,
            "avg_accuracy": avg_accuracy,
            "avg_completeness": avg_completeness,
            "detailed_results": self.results
        }

if __name__ == "__main__":
    async def main():
        evaluator = RetrievalEvaluator()
        report = await evaluator.run_benchmark()
        print(f"📊 Hit Rate @ 5: {report['hit_rate']:.2f}%")
        print(f"🏆 MRR: {report['mrr']:.3f}")
        print(f"🎯 Avg Accuracy: {report['avg_accuracy']:.2f}/5")
        print(f"📝 Avg Completeness: {report['avg_completeness']:.2f}/5")

    asyncio.run(main())