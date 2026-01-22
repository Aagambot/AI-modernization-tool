import lancedb
import pyarrow as pa
import networkx as nx
import os
import json
from pathlib import Path

class VectorStore:
    def __init__(self, db_path: str = None):
        project_root = Path(__file__).resolve().parent.parent
        if db_path is None:
            db_path = str(project_root / "code_index_db")
        
        self.graph_dir = project_root / "data" / "graphs"
        self.graph_dir.mkdir(parents=True, exist_ok=True)
        
        # KEY CHANGE: Path for the hash registry to support incremental indexing
        self.hash_path = project_root / "data" / "file_hashes.json"
        self.hash_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.db = lancedb.connect(db_path)
        self.table_name = "code_vectors"
        self.schema = pa.schema([
            pa.field("vector", pa.list_(pa.float32(), 768)),
            pa.field("content", pa.string()),
            pa.field("file_path", pa.string()),
            pa.field("name", pa.string())
        ])

    # --- Hash Management for Delta Indexing ---
    
    def load_hashes(self):
        """Loads the registry of processed file hashes."""
        if self.hash_path.exists():
            with open(self.hash_path, "r") as f:
                return json.load(f)
        return {}

    def save_hashes(self, hashes):
        """Saves the current file hashes to the registry."""
        with open(self.hash_path, "w") as f:
            json.dump(hashes, f, indent=4)

    def delete_file_vectors(self, file_path):
        """Removes existing vectors for a specific file to prevent duplicates."""
        table = self.get_table()
        if table:
            # LanceDB uses SQL-like predicates for deletion
            table.delete(f"file_path = '{file_path}'")

    # --- Existing Methods ---

    def save_graph(self, G, entity_name):
        path = self.graph_dir / f"{entity_name}_graph.gexf"
        nx.write_gexf(G, str(path))
        return str(path)

    def load_graph(self, entity_name):
        path = self.graph_dir / f"{entity_name}_graph.gexf"
        if path.exists():
            return nx.read_gexf(str(path))
        return None

    def get_neighbors(self, G, file_path):
        if not G or not G.has_node(file_path):
            return []
        neighbors = list(G.neighbors(file_path)) + list(G.predecessors(file_path))
        return list(set(neighbors))

    def get_table(self):
        try:
            return self.db.open_table(self.table_name)
        except Exception:
            return None
    
    def save_chunks(self, chunks, mode="add"):
        """Saves chunks with strict dimensional validation."""
        try:
            if self.table_name not in self.db.table_names():
                self.db.create_table(
                    self.table_name, 
                    data=chunks, 
                    schema=self.schema,
                    on_bad_vectors="drop" 
                )
            else:
                table = self.db.open_table(self.table_name)
                table.add(chunks, on_bad_vectors="drop")
            print(f"✅ Successfully updated {self.table_name}")
        except Exception as e:
            print(f"❌ Error saving to LanceDB: {e}")