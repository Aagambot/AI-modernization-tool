import lancedb
import pyarrow as pa
from pathlib import Path

class VectorStore:
    def __init__(self, db_path: str = None):
        # Path anchoring: Ensure code_index_db is always at project root
        if db_path is None:
            project_root = Path(__file__).resolve().parent.parent
            db_path = str(project_root / "code_index_db")
        
        self.db = lancedb.connect(db_path)
        self.table_name = "code_vectors"
        self.schema = pa.schema([
            pa.field("vector", pa.list_(pa.float32(), 768)),
            pa.field("content", pa.string()),
            pa.field("file_path", pa.string()),
            pa.field("name", pa.string())
        ])
    
    def get_table(self):
        """Returns the LanceDB table object."""
        try:
            return self.db.open_table(self.table_name)
        except Exception as e:
            print(f"❌ Could not open table: {e}")
            return None
    
    def save_chunks(self, chunks, mode="overwrite"):
        """
        Saves chunks and automatically drops any that have incorrect vector lengths.
        """
        try:
            self.db.create_table(
                self.table_name, 
                data=chunks, 
                schema=self.schema, 
                mode=mode,
                on_bad_vectors="drop"  # FIX: Automatically removes inconsistent vectors
            )
            print(f"✅ Successfully saved chunks to {self.table_name}")
        except Exception as e:
            print(f"❌ Error saving to LanceDB: {e}")
