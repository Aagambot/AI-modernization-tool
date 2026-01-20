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

# Updated Template to enforce your exact JSON schema
PROMPT_TEMPLATE = """
Act as a Senior ERPNext Architect conducting a System Assessment.
Explain the internal execution flow for {entity_name} during: "{user_query}"

CONTEXT DATA (Code & Call Graph):
{context_data}

STRICT OUTPUT FORMAT (JSON ONLY):
{{
  "event": "{user_query}",
  "executive_summary": "A 2-sentence overview of the primary goal of this event.",
  "execution_phases": {{
    "VALIDATION": [
      {{ "function": "...", "description": "...", "condition": "Mandatory/If POS/If Asset" }}
    ],
    "ACCOUNTING_LOGIC": [
      {{ "function": "...", "description": "...", "condition": "Mandatory/If Perpetual Inventory" }}
    ],
    "STOCK_LOGIC": [
      {{ "function": "...", "description": "...", "condition": "If update_stock is checked" }}
    ],
    "POST_SUBMISSION_HOOKS": [
      {{ "function": "...", "description": "...", "condition": "e.g., If Inter-company" }}
    ]
  }},
  "accounting_impact": "Summary of GL entries (Debtors, Sales, COGS, etc.)",
  "stock_impact": "Summary of Warehouse/Qty changes",
  "critical_business_rules": ["List the top 3-5 most important constraints identified"]
}}

INSTRUCTIONS:
1. Do not list every tiny function. Group related calls into the phases above.
2. Explicitly state the 'condition' for each step (e.g., Is it always executed or only in specific settings?).
3. Ensure the 'executive_summary' addresses the business intent.
"""
class ModernizationChat:
    def __init__(self, target_folder=None):
        self.api_key = os.getenv("GENAI_API_KEY")
        if not self.api_key:
            raise ValueError("❌ GENAI_API_KEY not found.")

        genai.configure(api_key=self.api_key)
        self.llm = genai.GenerativeModel('gemini-2.0-flash') 
        self.embedder = BGEEmbedder()
        self.store = VectorStore() 
        self.table = self.store.get_table()
        
        # We derive this dynamically in generate_domain_model
        self.entity_name = "SalesInvoice"
        
        print("💾 Pre-loading Graph into memory...")
        self.cached_graph = self.store.load_graph(self.entity_name)

    async def get_smart_context(self, query: str, limit: int = 5):
        metrics = {}
        t_start = time.perf_counter()

        # Step 1: Embedding
        t0 = time.perf_counter()
        query_vec_results = await asyncio.to_thread(self.embedder.embed_batch, [query])
        query_vec = query_vec_results[0]
        metrics['embedding_ms'] = (time.perf_counter() - t0) * 1000
        
        # Step 2: Vector Search
        t1 = time.perf_counter()
        results = await asyncio.to_thread(lambda: self.table.search(query_vec).limit(limit).to_list())
        metrics['vector_search_ms'] = (time.perf_counter() - t1) * 1000
        
        top_distance = results[0]['_distance'] if results else 1.0
        context_blocks = []
        global_seen_calls = set()
        
        t2 = time.perf_counter()
        
        for res in results:
            path = res['file_path']
            chunk_calls = []
            
            # Step 3: Deep Graph Extraction (Function-to-Function calls)
            if self.cached_graph:
                # Find nodes belonging to this file that are functions (contain ':')
                for node in self.cached_graph.nodes():
                    if node.startswith(path) and ":" in node:
                        # Find what this specific function calls
                        out_edges = self.cached_graph.out_edges(node)
                        for _, target in out_edges:
                            # Extract just the function name for the prompt
                            caller = node.split(":")[-1]
                            callee = target.split(":")[-1]
                            call_str = f"{caller} calls {callee}"
                            
                            if call_str not in global_seen_calls:
                                chunk_calls.append(call_str)
                                global_seen_calls.add(call_str)
                                if len(chunk_calls) > 10: break # Safety cap

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
        raw_name = folder_path.replace('\\', '/').rstrip('/').split('/')[-1]
        self.entity_name = "".join(x.title() for x in raw_name.split('_'))
        
        # Use the specific query if provided, else use a default summary query
        active_query = query if query else f"Analyze the core domain logic of {self.entity_name}"
        
        # Increase the limit to 8 to ensure we catch 'on_submit' and 'make_gl_entries'
        context, r_lat, _ = await self.get_smart_context(active_query, limit=8)

        final_prompt = PROMPT_TEMPLATE.format(
            entity_name=self.entity_name,
            user_query=active_query,
            context_data=json.dumps(context, indent=2)
        )
        start_gen = time.perf_counter()
        # Use JSON mode for structured response
        response = await self.llm.generate_content_async(
            final_prompt,
            generation_config={"response_mime_type": "application/json", "temperature": 0.1}
        )
        g_lat = (time.perf_counter() - start_gen) * 1000
        
        return response.text, r_lat , g_lat

async def main():
    try:
        chat = ModernizationChat()
        TARGET_DIR = r"C:/Users/Aagam/OneDrive/Desktop/erpnext/erpnext/accounts/doctype/sales_invoice"
        my_query = "What happens internally when a Sales Invoice is submitted in ERPNext?"
        print(f"🚀 Analyzing {TARGET_DIR}...")
        model_json, r_lat, g_lat = await chat.generate_domain_model(TARGET_DIR,query=my_query)
        
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