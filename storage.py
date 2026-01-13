import lancedb
import pandas as pd
from typing import List, Dict

class VectorStore:
    def __init__(self, db_path: str = "./code_index_db"):
        """
        Independent storage manager using LanceDB.
        """
        self.db_path = db_path
        self.table_name = "erpnext_chunks"
        self.uri = db_path
        self.db = lancedb.connect(self.uri)

    def save_chunks(self, embedded_chunks: List[Dict]):
        """
        Saves the chunks and vectors into a LanceDB table.
        """
        if not embedded_chunks:
            print("⚠️ No chunks to save.")
            return

        # 1. Convert list of dicts to a DataFrame for easy ingestion
        # LanceDB loves pandas DataFrames
        df = pd.DataFrame(embedded_chunks)

        # 2. Rename 'vector' column to 'vector' if not already, 
        # but our embedder already used 'vector'.
        
        # 3. Create or Overwrite the table
        try:
            tbl = self.db.create_table(self.table_name, data=df, mode="overwrite")
            print(f"✅ Successfully saved {len(df)} chunks to LanceDB at '{self.db_path}'")
        except Exception as e:
            print(f"❌ Storage Error: {e}")

    def search(self, query_vector: List[float], limit: int = 5):
        """
        Standalone search function to verify the data is there.
        """
        tbl = self.db.open_table(self.table_name)
        results = tbl.search(query_vector).limit(limit).to_list()
        return results

# --- STANDALONE TEST BLOCK ---
if __name__ == "__main__":
    # Mock data to test independence
    mock_data = [{
        "name": "test_node",
        "content": "def test(): pass",
        "vector": [0.1] * 1024, # BGE-Large dimension
        "type": "function",
        "start_line": 1
    }]
    
    store = VectorStore()
    store.save_chunks(mock_data)
    
    # Try a quick search to verify
    print("🔍 Testing retrieval...")
    res = store.search([0.1] * 1024, limit=1)
    if res:
        print(f"✨ Found item: {res[0]['name']}")