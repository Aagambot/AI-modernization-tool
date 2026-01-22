import requests

class BGEEmbedder:
    def embed_batch(self, texts: list):
        """Generates 768-dim vectors using nomic-embed-text via Ollama."""
        vectors = []
        for text in texts:
            try:
                response = requests.post(
                    "http://localhost:11434/api/embeddings", 
                    json={"model": "nomic-embed-text", "prompt": text},
                    timeout=30 
                )
                response.raise_for_status()
                embedding = response.json()['embedding']
                
                if len(embedding) == 768:
                    vectors.append(embedding)
                else:
                    print(f"⚠️ Warning: Model returned {len(embedding)} dims, expected 768.")
            except Exception as e:
                print(f"❌ Embedding error: {e}")
        return vectors