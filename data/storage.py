import lancedb
import pyarrow as pa
import networkx as nx
import os
import pickle
import json

class VectorStore:
    def __init__(self, db_path="code_index_db"):
        self.db_path = db_path
        self.db = lancedb.connect(self.db_path)
        self.table_name = "code_vectors"
        self.schema = pa.schema([
            pa.field("vector", pa.list_(pa.float32(), 768)),
            pa.field("id", pa.string()),           # Unique symbol ID
            pa.field("content", pa.string()),      # The code snippet
            pa.field("file_path", pa.string()),    # Source file
            pa.field("symbol_name", pa.string()),  # Function/Class name
            pa.field("symbol_type", pa.string()),  # 'class', 'method', etc.
            pa.field("hook_type", pa.string()),    # ERPNext hook (validate, etc.)
            pa.field("start_line", pa.int32()),    # Line number
            pa.field("end_line", pa.int32())       # Line number
        ])

    def get_table(self):
        """Opens or creates the table with the updated schema."""
        if self.table_name not in self.db.table_names():
            return self.db.create_table(self.table_name, schema=self.schema)
        return self.db.open_table(self.table_name)

    def save_chunks(self, chunks: list):
        """
        Saves AST-based chunks into LanceDB.
        Includes 'on_bad_vectors' handling for reliability.
        """
        table = self.get_table()
        if chunks:
            # LanceDB will automatically align these dicts to the Arrow schema
            table.add(chunks, on_bad_vectors="drop")

    def save_graph(self, G, entity_name):
        """Saves the NetworkX call graph for later retrieval."""
        graph_path = f"{entity_name}_graph.gpickle"
        with open(graph_path, 'wb') as f:
            pickle.dump(G, f)
        print(f"✅ Graph saved to {graph_path}")

    def load_graph(self, entity_name):
        """Loads the graph into memory for context expansion."""
        graph_path = f"{entity_name}_graph.gpickle"
        if os.path.exists(graph_path):
            with open(graph_path, 'rb') as f:
                return pickle.load(f)
        return None

    def check_file_hash(self, file_path, current_hash):
        """Placeholder for incremental indexing logic."""
        # You can implement a simple JSON or SQLite store for file hashes here
        return False

    def load_hashes(self):
        """Loads existing file hashes to check for changes."""
        hash_path = "file_hashes.json"
        if os.path.exists(hash_path):
            with open(hash_path, 'r') as f:
                return json.load(f)
        return {}

    def save_hashes(self, hashes: dict):
        """Persists the current file hashes."""
        hash_path = "file_hashes.json"
        with open(hash_path, 'w') as f:
            json.dump(hashes, f, indent=4)
        print(f"✅ File hashes saved to {hash_path}")

    def delete_file_vectors(self, file_path: str):
        """Removes old vectors for a file before re-indexing."""
        table = self.get_table()
        # LanceDB uses SQL-like filtering for deletions
        table.delete(f"file_path = '{file_path}'")