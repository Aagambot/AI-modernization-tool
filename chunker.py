from transformers import AutoTokenizer
import math
from typing import List, Dict

class HybridChunker:
    def __init__(self, model_name: str = "BAAI/bge-large-en-v1.5", max_tokens: int = 512, overlap: int = 50):
        """
        Independent Chunker that handles token-safe splitting.
        :param model_name: The exact model you'll use for embeddings.
        :param max_tokens: BGE-Large limit is 512.
        :param overlap: How many tokens to repeat between chunks.
        """
        # Load the actual tokenizer from HuggingFace to match BGE-Large logic
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.max_tokens = max_tokens
        self.overlap = overlap

    def process_nodes(self, nodes: List[Dict]) -> List[Dict]:
        """
        Takes the list from parser.py and returns token-sized chunks.
        """
        final_chunks = []
        for node in nodes:
            # 1. Convert code to tokens
            content = node['content']
            tokens = self.tokenizer.encode(content, add_special_tokens=False)
            token_count = len(tokens)

            # 2. Case A: Content fits in one BGE window
            if token_count <= self.max_tokens:
                node['token_count'] = token_count
                node['is_partial'] = False
                final_chunks.append(node)
            
            # 3. Case B: Content is too big (Hybrid Fallback)
            else:
                final_chunks.extend(self._sliding_window(node, tokens))
                
        return final_chunks

    def _sliding_window(self, node: Dict, tokens: List[int]) -> List[Dict]:
        """Splits large token arrays into overlapping windows."""
        sub_chunks = []
        step = self.max_tokens - self.overlap
        
        # Calculate how many pieces we need
        num_windows = math.ceil(len(tokens) / step)
        
        for i in range(num_windows):
            start = i * step
            end = start + self.max_tokens
            
            # Extract and decode back to text
            chunk_tokens = tokens[start:end]
            chunk_text = self.tokenizer.decode(chunk_tokens)
            
            sub_chunks.append({
                'name': f"{node['name']}_part_{i+1}",
                'type': node['type'],
                'content': chunk_text,
                'start_line': node['start_line'], # Original start line
                'token_count': len(chunk_tokens),
                'is_partial': True
            })
            
            # Break if we've reached the end
            if end >= len(tokens):
                break
                
        return sub_chunks

# --- STANDALONE TEST BLOCK ---
if __name__ == "__main__":
    # Test independence with a mock "node" from the parser
    mock_node = {
        'name': 'god_function',
        'type': 'function_definition',
        'start_line': 10,
        'content': "def god_function():\n" + "    print('I am very long...')\n" * 200
    }
    
    chunker = HybridChunker(max_tokens=100) # Small limit for testing
    chunks = chunker.process_nodes([mock_node])
    
    print(f"✅ Chunking Complete.")
    print(f"Original was ~{len(mock_node['content'].split())} words.")
    print(f"Produced {len(chunks)} token-safe chunks.")
    
    for i, c in enumerate(chunks[:2]):
        print(f"\n--- Chunk {i+1} ({c['token_count']} tokens) ---")
        print(c['content'][:150] + "...")