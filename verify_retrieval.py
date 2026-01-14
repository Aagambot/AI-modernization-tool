import json
import time
from storage import VectorStore  # Your existing LanceDB store
from embedder import BGEEmbedder # Your existing embedder
import os
def verify_rag_performance(golden_data_path):
    store = VectorStore()
    embedder = BGEEmbedder()
    
    with open(golden_data_path, 'r') as f:
        golden_queries = json.load(f)

    results = []
    hits_at_5 = 0
    reciprocal_ranks = []

    print(f"🧪 Evaluating {len(golden_queries)} Golden Queries...\n")

    for item in golden_queries:
        query = item['query']
        expected = item['expected_file']
        
        # 1. Search Vector DB
        start_time = time.time()
        query_vector = embedder.embed_batch([query])[0]
        table = store.get_table()
        if table:
            search_results = table.search(query_vector).limit(5).to_list()
        else:
            print("❌ Table not found. Did you run the indexer first?")
            return
        latency = (time.time() - start_time) * 1000

        # 2. Check Rank
        rank = 0
        found = False
        for i, res in enumerate(search_results):
            actual_path = res.get('file_path', '').replace('\\', '/').lower()
            expected_path = expected.replace('\\', '/').lower()
            print(f"DEBUG: Found {res.get('file_path')} | Expected {expected}")
            if expected_path in actual_path:
                    rank = i + 1
                    found = True
                    break
        
        # 3. Calculate Metrics
        if found:
            hits_at_5 += 1
            reciprocal_ranks.append(1.0 / rank)
        else:
            reciprocal_ranks.append(0.0)

        results.append({
            "query": query,
            "found": found,
            "rank": rank if found else "N/A",
            "latency_ms": latency
        })

    # Final Aggregates
    final_hit_rate = (hits_at_5 / len(golden_queries)) * 100
    final_mrr = sum(reciprocal_ranks) / len(golden_queries)

    print(f"📊 --- FINAL WEEK 1 REPORT ---")
    print(f"✅ Hit Rate @ 5: {final_hit_rate:.2f}%")
    print(f"🏆 Mean Reciprocal Rank (MRR): {final_mrr:.3f}")
    return results

if __name__ == "__main__":
    verify_rag_performance("golden_dataset.json")