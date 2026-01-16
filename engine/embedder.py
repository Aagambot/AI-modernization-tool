import requests

class BGEEmbedder:
    def embed_batch(self, texts: list):
        """Generates 1024-dim vectors for a list of strings."""
        vectors = []
        for text in texts:
            response = requests.post("http://localhost:11434/api/embeddings", 
                                     json={"model": "nomic-embed-text", "prompt": text})
            vectors.append(response.json()['embedding'])
        return vectors
