import requests

class BGEEmbedder:
    def __init__(self, model_name: str = "nomic-embed-text"):
        self.model_name = model_name
        self.url = "http://localhost:11434/api/embeddings"

    def embed_batch(self, texts: list, is_query: bool = False):
        """
        Generates 768-dim vectors via Ollama. 
        Aligned with Phase 1 Indexing architecture.
        """
        vectors = []
        # Nomic performs better with task-specific prefixes
        prefix = "search_query: " if is_query else "search_document: "
        
        for text in texts:
            try:
                # Prepend prefix to improve retrieval precision
                payload = {
                    "model": self.model_name, 
                    "prompt": f"{prefix}{text}"
                }
                
                response = requests.post(self.url, json=payload, timeout=30)
                response.raise_for_status()
                embedding = response.json()['embedding']
                
                # Validation against the LanceDB schema
                if len(embedding) == 768:
                    vectors.append(embedding)
                else:
                    print(f"⚠️ Warning: Model returned {len(embedding)} dims, expected 768.")
                    # Fallback or padding could be added here if needed
            except Exception as e:
                print(f"❌ Embedding error: {e}")
                
        return vectors