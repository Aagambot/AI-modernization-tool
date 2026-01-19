import lancedb
import pyarrow as pa
import networkx as nx
import os
from pathlib import Path

class VectorStore:
    def __init__(self, db_path: str = None):
        # Path anchoring: Ensure code_index_db is always at project root
        project_root = Path(__file__).resolve().parent.parent
        if db_path is None:
            db_path = str(project_root / "code_index_db")
        
        # Initialize directories
        self.graph_dir = project_root / "data" / "graphs"
        self.graph_dir.mkdir(parents=True, exist_ok=True)
        
        self.db = lancedb.connect(db_path)
        self.table_name = "code_vectors"
        self.schema = pa.schema([
            pa.field("vector", pa.list_(pa.float32(), 768)),
            pa.field("content", pa.string()),
            pa.field("file_path", pa.string()),
            pa.field("name", pa.string())
        ])

    def save_graph(self, G, entity_name):
        """Saves the NetworkX graph as a GEXF data product."""
        path = self.graph_dir / f"{entity_name}_graph.gexf"
        nx.write_gexf(G, str(path))
        return str(path)

    def load_graph(self, entity_name):
        """Loads the graph from the data folder for chat retrieval."""
        path = self.graph_dir / f"{entity_name}_graph.gexf"
        if path.exists():
            return nx.read_gexf(str(path))
        return None

    def get_neighbors(self, G, file_path):
        """Finds callers and callees for Graph-Augmented Retrieval."""
        if not G or not G.has_node(file_path):
            return []
        # In a directed graph, neighbors are callees; predecessors are callers
        neighbors = list(G.neighbors(file_path)) + list(G.predecessors(file_path))
        return list(set(neighbors))

    def get_table(self):
        """Returns the LanceDB table object."""
        try:
            return self.db.open_table(self.table_name)
        except Exception as e:
            return None
    
    def save_chunks(self, chunks, mode="overwrite"):
        """Saves chunks to LanceDB with schema validation."""
        try:
            self.db.create_table(
                self.table_name, 
                data=chunks, 
                schema=self.schema, 
                mode=mode,
                on_bad_vectors="drop"
            )
            print(f"✅ Successfully saved chunks to {self.table_name}")
        except Exception as e:
            print(f"❌ Error saving to LanceDB: {e}")