from data.storage import VectorStore
from engine.embedder import BGEEmbedder

class CodeSearcher:
    def __init__(self):
        self.store = VectorStore()
        self.embedder = BGEEmbedder()
        self.table = self.store.db.open_table(self.store.table_name)

    def search(self, query: str, limit: int = 5):
        query_vec = self.embedder.embed_batch([query])[0]
        return self.table.search(query_vec).limit(limit).to_list()
