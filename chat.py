import os
import time
import json
import asyncio
import networkx as nx
import lancedb
import google.generativeai as genai
from engine.embedder import BGEEmbedder 
from data.storage import VectorStore 
from dotenv import load_dotenv
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

load_dotenv()

TEMPLATES = {
    "summary": """
        Act as a Technical Architect. Provide a high-level Domain Model for {entity_name}.
        Focus on: Fields, Core Methods, and Primary Business Rules.
        CONTEXT: {context_data}
    """,
    "process_flow": """
        Act as a Senior System Analyst. Explain the step-by-step internal execution flow 
        for {user_query} in {entity_name}. Group by VALIDATION, ACCOUNTING, and STOCK phases.
        CONTEXT: {context_data}
    """,
    "debugging": """
        Act as a Lead Developer. Help me understand the specific logic for: {user_query}.
        Trace the dependencies and potential failure points in {entity_name}.
        CONTEXT: {context_data}
    """
}

class ModernizationChat:
    def __init__(self, target_folder=None):
        self.api_key = os.getenv("GENAI_API_KEY")
        if not self.api_key:
            raise ValueError("❌ GENAI_API_KEY not found.")

        genai.configure(api_key=self.api_key)
        self.llm = genai.GenerativeModel('gemini-2.0-flash') 
        self.embedder = BGEEmbedder()
        self.store = VectorStore() 
        
        
        self._table = None 
        
        self.entity_name = "SalesInvoice"
        
        print("💾 Pre-loading Graph into memory...")
        self.cached_graph = self.store.load_graph(self.entity_name)
    
    def compute_mmr(self,query_embedding, candidate_embeddings, lambda_param, top_k=8):
        """
        Core MMR Algorithm:
        lambda_param: 1.0 is pure relevance, 0.0 is pure diversity.
        """
        if not candidate_embeddings:
            return []

        selected_indices = []
        candidate_indices = list(range(len(candidate_embeddings)))

        # Calculate similarities between query and all candidates
        query_sims = cosine_similarity([query_embedding], candidate_embeddings)[0]

        # Pick the best candidate first
        first_best = np.argmax(query_sims)
        selected_indices.append(first_best)
        candidate_indices.remove(first_best)

        while len(selected_indices) < top_k and candidate_indices:
            mmr_scores = []
            for cand_idx in candidate_indices:
                # Relevance score
                relevance = query_sims[cand_idx]
                
                # Diversity score (similarity to already selected chunks)
                target_cand_emb = [candidate_embeddings[cand_idx]]
                selected_embs = [candidate_embeddings[i] for i in selected_indices]
                redundancy = np.max(cosine_similarity(target_cand_emb, selected_embs))
                
                # MMR Formula
                score = lambda_param * relevance - (1 - lambda_param) * redundancy
                mmr_scores.append((score, cand_idx))

            # Select the candidate with the best MMR score
            next_best = max(mmr_scores, key=lambda x: x[0])[1]
            selected_indices.append(next_best)
            candidate_indices.remove(next_best)

        return selected_indices

    @property
    def table(self):
        """Lazy-load the table from the store only when accessed."""
        if self._table is None:
            self._table = self.store.get_table()
        return self._table

    async def get_smart_context(self, query: str, limit: int = 8):
        if self.table is None:
            return "Error: Vector table not found. Please run ingestion first.", 0, 0
            
        metrics = {}
        t_start = time.perf_counter()
        technical_keywords = ["function", "logic", "code", "method", "how", "where", "algorithm", "class"]
        is_technical_query = any(word in query.lower() for word in technical_keywords)
        # Step 1: Embedding
        t0 = time.perf_counter()
        query_vec_results = await asyncio.to_thread(self.embedder.embed_batch, [query])
        query_vec = query_vec_results[0]
        metrics['embedding_ms'] = (time.perf_counter() - t0) * 1000
        
        # Step 2: Vector Search with Candidate Oversampling
        candidate_limit = 20 
        t1 = time.perf_counter()
        def perform_search():
            search_query = self.table.search(query_vec).limit(20)
            
            # If it's a technical query, filter out non-python files
            if is_technical_query:
                # LanceDB uses SQL-like predicates
                search_query = search_query.where("file_path LIKE '%.py'")
                
            return search_query.to_list()
        initial_results = await asyncio.to_thread(perform_search)
        metrics['vector_search_ms'] = (time.perf_counter() - t1) * 1000

        # Step 3: Apply MMR Re-ranking
        if initial_results and len(initial_results) > limit:  
            candidate_embs = [res['vector'] for res in initial_results] 
            selected_indices = self.compute_mmr(
                query_vec,          
                candidate_embs,     
                lambda_param=0.5,   
                top_k=limit 
            )
            results = [initial_results[i] for i in selected_indices]
        
        top_distance = results[0]['_distance'] if results else 1.0
        context_blocks = []
        global_seen_calls = set()
        
        t2 = time.perf_counter()
        
        # Step 4: Context Assembly (Existing logic)
        for res in results:
            path = res['file_path']
            chunk_calls = []
            
            if self.cached_graph:
                for node in self.cached_graph.nodes():
                    if node.startswith(path) and ":" in node:
                        out_edges = self.cached_graph.out_edges(node)
                        for _, target in out_edges:
                            caller = node.split(":")[-1]
                            callee = target.split(":")[-1]
                            call_str = f"{caller} calls {callee}"
                            
                            if call_str not in global_seen_calls:
                                chunk_calls.append(call_str)
                                global_seen_calls.add(call_str)
                                if len(chunk_calls) > 10: break 

            context_blocks.append({
                "file": path,
                "confidence": round(1 - top_distance, 2),
                "call_relationships": chunk_calls,
                "code": res['content'][:5000]
            })
        
        metrics['graph_lookup_ms'] = (time.perf_counter() - t2) * 1000
        total_retrieval_ms = (time.perf_counter() - t_start) * 1000
        
        return context_blocks, total_retrieval_ms, metrics
    

    
    async def generate_domain_model(self, folder_path, query=None):
        intent_prompt = f"Categorize this user query into 'summary', 'process_flow', or 'debugging': {query}"
        intent_resp = self.llm.generate_content(intent_prompt)
        intent = intent_resp.text.strip().lower()
        if query:
            query_lower = query.lower()
            if any(word in query_lower for word in ["how", "flow", "process", "submit", "step"]):
                intent = "process_flow"
            elif any(word in query_lower for word in ["where", "debug", "function", "logic", "which", "allocat"]):
                intent = "debugging"

        active_query = query if query else f"Overview of {self.entity_name}"
        context, r_lat, _ = await self.get_smart_context(active_query, limit=8)

        selected_template = TEMPLATES.get(intent, TEMPLATES["summary"])
        
        final_prompt = selected_template.format(
            entity_name=self.entity_name,
            user_query=active_query,
            context_data=json.dumps(context, indent=2)
        )

        start_gen = time.perf_counter()
        response = await self.llm.generate_content_async(
            final_prompt,
            generation_config={"response_mime_type": "application/json", "temperature": 0.1}
        )
        g_lat = (time.perf_counter() - start_gen) * 1000

        return response.text, r_lat, g_lat
    
async def main():
    try:
        chat = ModernizationChat()
        # TARGET_DIR is technically dynamic but we focus on the indexed module
        TARGET_DIR = r"C:/Users/Aagam/OneDrive/Desktop/erpnext/erpnext/accounts/doctype/sales_invoice"
        my_query = "Which function allocates advance payments against a Sales Invoice?"
        print(f"🚀 Analyzing {TARGET_DIR}...")
        model_json, r_lat, g_lat = await chat.generate_domain_model(TARGET_DIR, query=my_query)
        
        output = json.loads(model_json)
        print("\n✅ EXTRACTED DOMAIN MODEL:")
        print(json.dumps(output, indent=4))
        
        print("\n" + "="*40)
        print(f"⏱️ TOTAL Retrieval: {r_lat:.2f}ms")
        print(f"⏱️ TOTAL Generation (API): {g_lat:.2f}ms")
        print("="*40)  
    except Exception as e:
        print(f"❌ Critical Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())