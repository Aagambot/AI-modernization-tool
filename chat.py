import os
import time
import json
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
        self.llm = genai.GenerativeModel('gemini-2.5-flash') 
        self.embedder = BGEEmbedder()
        self.store = VectorStore() 
        self.table = self.store.get_table()
        
        # Determine current entity name
        self.entity_name = "SalesInvoice"

    def get_smart_context(self, query: str, limit: int = 3):
        """
        Implements Adaptive RAG: Uses Confidence Scores to trigger Graph Research.
        """
        start_time = time.time()
        query_vec = self.embedder.embed_batch([query])[0]
        
        # 1. Standard Vector Search
        results = self.table.search(query_vec).limit(limit).to_list()
        latency_ms = (time.time() - start_time) * 1000
        
        # 2. Confidence Check (Distance Score)
        # LanceDB '_distance': lower is better. 0.4-0.5 is a common threshold for 'uncertainty'.
        top_distance = results[0]['_distance'] if results else 1.0
        
        context_blocks = []
        use_graph = top_distance > 0.45
        
        # Load Graph only if needed to save memory/time
        G = self.store.load_graph(self.entity_name) if use_graph else None

        for res in results:
            path = res['file_path']
            deps = []
            
            # 3. Graph Augmentation
            if G and G.has_node(path):
                # Fetch callers and callees (neighbors) to provide 'Modernization' context
                deps = self.store.get_neighbors(G, path)
            
            context_blocks.append({
                "file": path,
                "confidence": round(1 - top_distance, 2),
                "graph_enriched": use_graph,
                "related_files": deps[:5],
                "code": res['content']
            })
        
        return context_blocks, latency_ms, use_graph

    def generate_domain_model(self, folder_path):
        raw_name = folder_path.replace('\\', '/').split('/')[-1]
        self.entity_name = "".join(x.title() for x in raw_name.split('_'))
        
        # 1. Retrieve enriched context
        query = f"Explain the core domain logic and state transitions of {self.entity_name}"
        context, r_lat, graph_triggered = self.get_smart_context(query)

        if graph_triggered:
            print(f"🔍 Low vector confidence ({context[0]['confidence']}). Activated Graph Research.")

        # 2. Build Prompt
        final_prompt = PROMPT_TEMPLATE.format(
            entity_name=self.entity_name,
            context_data=json.dumps(context, indent=2)
        )

        # 3. LLM Generation
        start_gen = time.time()
        response = self.llm.generate_content(
            final_prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        g_lat = (time.time() - start_gen) * 1000

        return response.text, r_lat, g_lat

if __name__ == "__main__":
    try:
        chat = ModernizationChat()
        TARGET_DIR = r"C:/Users/Aagam/OneDrive/Desktop/erpnext/erpnext/accounts/doctype/sales_invoice"
        
        print(f"🚀 Analyzing {TARGET_DIR}...")
        model_json, r_lat, g_lat = chat.generate_domain_model(TARGET_DIR)
        
        output = json.loads(model_json)
        print("\n✅ EXTRACTED DOMAIN MODEL:")
        print(json.dumps(output, indent=4))
        
        print("\n" + "="*40)
        print(f"⏱️ Retrieval Latency: {r_lat:.2f}ms")
        print(f"⏱️ Generation Latency: {g_lat:.2f}ms")
        print("="*40)  
    except Exception as e:
        print(f"❌ Critical Error: {e}")