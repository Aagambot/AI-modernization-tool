import os
import time
import json
import networkx as nx
import lancedb
import google.generativeai as genai
from engine.embedder import BGEEmbedder 
from dotenv import load_dotenv
#change the prompt template to match requirements
load_dotenv()
PROMPT_TEMPLATE = """
    Act as an MCP Context Provider. Generate a technical specification for {entity_name} to be used by a coding agent (Cursor).

    FORMAT: Use a hierarchical tree with one-line functional descriptions.

    STRUCTURE:
    1. ENTRY POINT: Define the exact file:line for the .submit() anchor.
    2. PHASE-BASED WORKFLOW:
    - [VALIDATION]: Rules that guard state.
    - [ACCOUNTING]: Ledger/GL impact.
    - [STOCK]: Inventory/Valuation impact.
    - [HOOKS]: Background jobs and side effects.
    3. CONTEXTUAL OVERLAYS:
    - Mention specific PRs, Jira issues, or "Quirks" found in comments.

    CONSTRAINT: Every method MUST have a single-line explanation following a '→' symbol.
    Example: make_gl_entries() → orchestrates the creation of debit/credit lines for the ledger.

    OUTPUT: Return only the structured JSON representation of this domain model.
"""

class ModernizationChat:
    # In your chat.py, define this as a constant

    def __init__(self,target_folder=None):
        # 1. Fetch Key from Environment
        self.api_key = os.getenv("GENAI_API_KEY")
        self.target_folder = target_folder
        if not self.api_key:
            raise ValueError("❌ Error: GENAI_API_KEY not found in environment variables.")

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

    def generate_domain_model(self, folder_path):
        # Dynamically determine entity name from path (e.g., "sales_invoice" -> "SalesInvoice")
        raw_name = folder_path.split('/')[-1]
        entity_name = "".join(x.title() for x in raw_name.split('_'))
        
        # 1. Get Context (RAG)
        query = f"{entity_name} schema and core logic"
        context, r_lat = self.get_context(query)

        # 2. Fill the Template
        final_prompt = PROMPT_TEMPLATE.format(
            entity_name=entity_name,
            context_data=json.dumps(context)
        )

        # 3. Generate
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
        print("🚀 Starting Domain Model Extraction")
        TARGET_DIR = r"C:/Users/Aagam/OneDrive/Desktop/erpnext/erpnext/accounts/doctype/sales_invoice"
        model_json, r_lat, g_lat = chat.generate_domain_model(TARGET_DIR)
        
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