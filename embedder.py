import requests
from typing import List, Dict

class BGEEmbedder:
    def __init__(self, model_name: str = "bge-large"):
        """
        Independent Embedder that talks to the local Ollama API.
        """
        self.model_name = model_name
        self.url = "http://localhost:11434/api/embeddings"

    def embed_chunks(self, chunks: List[Dict]) -> List[Dict]:
        """
        Takes the token-safe chunks and adds 1024-dimension vectors.
        """
        embedded_results = []
        
        print(f"🚀 Starting embedding with {self.model_name}...")

        for chunk in chunks:
            try:
                response = requests.post(
                    self.url,
                    json={
                        "model": self.model_name,
                        "prompt": chunk['content']
                    },
                    timeout=30
                )
                response.raise_for_status()
                
                # Add the embedding vector to our chunk dictionary
                chunk['vector'] = response.json()['embedding']
                embedded_results.append(chunk)
                
            except Exception as e:
                print(f"❌ Error embedding chunk {chunk.get('name')}: {e}")
                # We skip failed chunks to keep the pipeline moving
                continue
        
        print(f"✅ Successfully embedded {len(embedded_results)} chunks.")
        return embedded_results

# --- STANDALONE TEST BLOCK ---
if __name__ == "__main__":
    # Test if Ollama is working with a simple dummy chunk
    test_chunks = [{
        "name": "test_func",
        "content": "def hello_world(): print('Hello from Ollama')"
    }]
    
    embedder = BGEEmbedder()
    results = embedder.embed_chunks(test_chunks)
    
    if results and 'vector' in results[0]:
        print(f"✨ Success! Vector Dimension: {len(results[0]['vector'])}")
        print(f"First 5 numbers: {results[0]['vector'][:5]}")