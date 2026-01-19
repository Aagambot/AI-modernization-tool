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

load_dotenv()

PROMPT_TEMPLATE = """
Act as an MCP Context Provider. Generate a technical specification for {entity_name}.
Use the provided CODE CONTEXT and RELATED DEPENDENCIES to build the model.

CONTEXT DATA:
{context_data}

FORMAT: Use a hierarchical tree with one-line functional descriptions.
STRUCTURE:
1. ENTRY POINT: Define the exact file:line for the .submit() anchor.
2. PHASE-BASED WORKFLOW: [VALIDATION], [ACCOUNTING], [STOCK], [HOOKS].
3. CONTEXTUAL OVERLAYS: Mention specific PRs or "Quirks".

CONSTRAINT: Every method MUST have a single-line explanation following a '→'.
OUTPUT: Return only the structured JSON representation.
"""

class ModernizationChat:
    def __init__(self, target_folder=None):
        self.api_key = os.getenv("GENAI_API_KEY")
        if not self.api_key:
            raise ValueError("❌ GENAI_API_KEY not found.")

        genai.configure(api_key=self.api_key)
        # Using the async-compatible model
        self.llm = genai.GenerativeModel('gemini-2.0-flash') 
        self.embedder = BGEEmbedder()
        self.store = VectorStore() 
        self.table = self.store.get_table()
        
        self.entity_name = "SalesInvoice"
        
        print("💾 Pre-loading Graph into memory...")
        self.cached_graph = self.store.load_graph(self.entity_name)

    async def get_smart_context(self, query: str, limit: int = 3):
        """
        Runs Embedding and Graph logic concurrently to hide latency.
        """
        metrics = {}
        t_start = time.perf_counter()

        # Step 1: Run Embedding and initial Graph check in parallel
        t0 = time.perf_counter()
        query_vec_task = asyncio.to_thread(self.embedder.embed_batch, [query])
        
        # While waiting for embedding, we can do other prep work if needed
        query_vec_results = await query_vec_task
        query_vec = query_vec_results[0]
        metrics['embedding_ms'] = (time.perf_counter() - t0) * 1000
        
        # Step 2: Search Vector DB (also offloaded to a thread)
        t1 = time.perf_counter()
        results = await asyncio.to_thread(lambda: self.table.search(query_vec).limit(limit).to_list())
        metrics['vector_search_ms'] = (time.perf_counter() - t1) * 1000
        
        top_distance = results[0]['_distance'] if results else 1.0
        use_graph = top_distance > 0.45
        
        context_blocks = []
        t2 = time.perf_counter()
        
        if use_graph and self.cached_graph:
            # Graph lookups are usually fast, but we keep them clean
            for res in results:
                path = res['file_path']
                deps = self.store.get_neighbors(self.cached_graph, path) if self.cached_graph.has_node(path) else []
                context_blocks.append({
                    "file": path, "confidence": round(1 - top_distance, 2),
                    "graph_enriched": True, "related_files": deps[:5], "code": res['content']
                })
        else:
            for res in results:
                context_blocks.append({
                    "file": res['file_path'], "confidence": round(1 - top_distance, 2),
                    "graph_enriched": False, "code": res['content']
                })
        
        metrics['graph_lookup_ms'] = (time.perf_counter() - t2) * 1000
        total_retrieval_ms = (time.perf_counter() - t_start) * 1000
        
        return context_blocks, total_retrieval_ms, use_graph, metrics

    async def generate_domain_model(self, folder_path):
        raw_name = folder_path.replace('\\', '/').split('/')[-1]
        self.entity_name = "".join(x.title() for x in raw_name.split('_'))
        
        query = f"Explain the core domain logic and state transitions of {self.entity_name}"
        
        # 1. Retrieve context asynchronously
        context, r_lat, graph_triggered, r_metrics = await self.get_smart_context(query)

        # 2. Build Prompt
        final_prompt = PROMPT_TEMPLATE.format(
            entity_name=self.entity_name,
            context_data=json.dumps(context, indent=2)
        )

        # 3. Use Async LLM Generation
        start_gen = time.perf_counter()
        response = await self.llm.generate_content_async(
            final_prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        g_lat = (time.perf_counter() - start_gen) * 1000

        return response.text, r_lat, g_lat

async def main():
    try:
        chat = ModernizationChat()
        TARGET_DIR = r"C:/Users/Aagam/OneDrive/Desktop/erpnext/erpnext/accounts/doctype/sales_invoice"
        
        print(f"🚀 Analyzing {TARGET_DIR}...")
        model_json, r_lat, g_lat = await chat.generate_domain_model(TARGET_DIR)
        
        output = json.loads(model_json)
        print("\n✅ EXTRACTED DOMAIN MODEL:")
        print(json.dumps(output, indent=4))
        
        print("\n" + "="*40)
        print(f"⏱️ TOTAL Retrieval: {r_lat:.2f}ms")
        print(f"⏱️ TOTAL Generation (API): {g_lat:.2f}ms")
        print("="*40)  
    except Exception as e:
        print(f"❌ Critical Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())