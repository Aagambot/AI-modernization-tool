import networkx as nx
import lancedb
import requests
import json
import time
from embedder import BGEEmbedder

class ModernizationChat:
    def __init__(self):
        self.embedder = BGEEmbedder()
        self.db = lancedb.connect("./code_index_db")
        self.table = self.db.open_table("code_vectors")
        try:
            self.G = nx.read_gexf("sales_invoice_graph.gexf")
        except:
            self.G = nx.DiGraph()

    def get_context(self, query: str):
        start_time = time.time()
        query_vec = self.embedder.embed_batch([query])[0]
        
        # PERFORMANCE: limit to 3 high-quality chunks to keep prompt light
        results = self.table.search(query_vec).limit(3).to_list()
        latency = (time.time() - start_time) * 1000
        
        context_blocks = []
        for res in results:
            # Metadata-First: Extract function signatures and docfields only
            # This prevents prompt overflow and focuses on "Logic Findability"
            context_blocks.append({
                "file": res['file_path'],
                "content": res['content'][:3000] # Increased for better logic coverage
            })
        return context_blocks, latency

    def extract_domain_model(self):
        # ANCHOR QUERY: Forces retrieval of both JSON metadata and Python logic
        context, lat = self.get_context("Sales Invoice docfields fields validate on_submit controllers")

        prompt = f"""
        You are a software architect. Extract the structural domain model from this ERPNext code.
        
        RULES:
        1. If you see a list of 'fields' in a JSON-like structure, extract their 'fieldname' and 'fieldtype'.
        2. Identify core methods (e.g., validate, on_submit) and their outgoing calls.
        3. Isolate business rules (e.g., credit limit checks).

        CONTEXT:
        {json.dumps(context)}

        RESPONSE FORMAT (JSON ONLY):
        {{
            "entity": "SalesInvoice",
            "fields": [{{ "name": "...", "type": "..." }}],
            "methods": [{{ "name": "...", "calls": [] }}],
            "business_rules": []
        }}
        """

        response = requests.post("http://localhost:11434/api/generate", 
                                 json={
                                     "model": "llama3.2:latest", 
                                     "prompt": prompt, 
                                     "stream": False,
                                     "format": "json", # Forces JSON mode in Ollama
                                     "options": {
                                         "temperature": 0, # Makes output predictable
                                         "num_ctx": 8192   # Ensures enough room for schema
                                     }
                                 })
        return response.json().get('response', '{}'), lat

if __name__ == "__main__":
    chat = ModernizationChat()
    print("🧠 Performing Structural Extraction...")
    model_json, latency = chat.extract_domain_model()
    print(model_json)
    print(f"\n⏱️ Retrieval Latency: {latency:.2f}ms")