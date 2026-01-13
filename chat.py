import os
import time
import json
import networkx as nx
import lancedb
import google.generativeai as genai
from embedder import BGEEmbedder 
from dotenv import load_dotenv
class ModernizationChat:
    def __init__(self):
        # 1. Fetch Key from Environment
        # Note: Added a check to ensure the key is actually found
        load_dotenv()
        self.api_key = os.getenv("GENAI_API_KEY")
        if not self.api_key:
            raise ValueError("❌ Error: GENAI_API_KEY not found in environment variables.")

        # 2. Configure Gemini explicitly with the API Key
        # This prevents the 'Insufficient Scopes' error by bypassing ADC
        genai.configure(api_key=self.api_key)
        self.llm = genai.GenerativeModel('gemini-2.5-flash')
        
        # 3. Initialize local intelligence (Embedder + Vector DB + Graph)
        self.embedder = BGEEmbedder()
        self.db = lancedb.connect("./code_index_db")
        self.table = self.db.open_table("code_vectors")
        
        try:
            self.G = nx.read_gexf("sales_invoice_graph.gexf")
        except Exception:
            self.G = nx.DiGraph()

    def get_context(self, query: str, limit: int = 5):
        """Retrieves code chunks and enriches with Graph dependencies."""
        start_time = time.time()
        query_vec = self.embedder.embed_batch([query])[0]
        results = self.table.search(query_vec).limit(limit).to_list()
        latency_ms = (time.time() - start_time) * 1000
        
        context_blocks = []
        for res in results:
            path = res['file_path']
            deps = []
            if self.G.has_node(path):
                deps = [t for _, t, d in self.G.out_edges(path, data=True)]

            context_blocks.append({
                "file": path,
                "global_calls": deps[:10],
                "code": res['content']
            })
        
        return context_blocks, latency_ms

    def generate_domain_model(self):
            query = "Sales Invoice fields types and on_submit call chain"
            context, r_lat = self.get_context(query, limit=7)

            # THE "GOLD STANDARD" EXAMPLE (Few-Shot)
            example_format = {
                "entity": "SalesInvoice",
                "fields": [{"name": "customer", "type": "Link", "target": "Customer"}],
                "methods": [{"name": "validate", "calls": ["check_credit_limit"]}],
                "business_rules": ["Credit limit check before save"]
            }

            prompt = f"""
            Analyze the ERPNext code context and return a Domain Model.
            
            STRICT FORMAT REQUIRED:
            Follow this structure exactly: {json.dumps(example_format)}

            - 'fields': Find the exact 'fieldtype' from the code (Link, Date, Currency, etc.).
            - 'methods': Identify which functions are called INSIDE validate and on_submit.
            
            CONTEXT:
            {json.dumps(context)}
            """

            start_gen = time.time()
            response = self.llm.generate_content(
                prompt, 
                generation_config={"response_mime_type": "application/json"}
            )
            g_lat = (time.time() - start_gen) * 1000
            
            return response.text, r_lat, g_lat

if __name__ == "__main__":
    try:
        chat = ModernizationChat()
        print("🚀 Starting Domain Model Extraction")
        
        model_json, r_lat, g_lat = chat.generate_domain_model()
        
        # Parse and Prettify
        output = json.loads(model_json)
        print("\n✅ EXTRACTED DOMAIN MODEL:")
        print(json.dumps(output, indent=4))
        
        print("\n" + "="*40)
        print(f"⏱️ Retrieval Latency: {r_lat:.2f}ms")
        print(f"⏱️ Generation Latency: {g_lat:.2f}ms")
        print("="*40)  
    except Exception as e:
        print(f"❌ Critical Error: {e}")