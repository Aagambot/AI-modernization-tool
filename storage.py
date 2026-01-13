import lancedb
import pyarrow as pa

class VectorStore:
    def __init__(self, db_path: str = "./code_index_db"):
        self.db = lancedb.connect(db_path)
        self.table_name = "code_vectors"
        # BGE-Large uses 1024 dimensions
        self.schema = pa.schema([
            pa.field("vector", pa.list_(pa.float32(), 1024)),
            pa.field("content", pa.string()),
            pa.field("file_path", pa.string()),
            pa.field("name", pa.string())
        ])

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