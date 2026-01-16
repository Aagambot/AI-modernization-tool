from transformers import AutoTokenizer
import requests
import math
from typing import List, Dict

class HybridChunker:
    def __init__(self, model_name: str = "nomic-embed-text", max_tokens: int = 2048, overlap: int = 150):
        """
        Refactored Chunker optimized for Nomic's 2048 context window.
        Uses BERT tokenizer locally to ensure alignment with Nomic's architecture.
        """
        # Load the actual tokenizer from HuggingFace
        self.tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased")
        self.max_tokens = max_tokens
        self.overlap = overlap

    def split_text(self, text: str) -> List[str]:
        """
        FIX: Added this method to handle raw strings from main.py.
        Returns a list of strings, each within the token limit.
        """
        tokens = self.tokenizer.encode(text, add_special_tokens=False)
        if len(tokens) <= self.max_tokens:
            return [text]

        chunks = []
        step = self.max_tokens - self.overlap
        for i in range(0, len(tokens), step):
            chunk_tokens = tokens[i : i + self.max_tokens]
            chunks.append(self.tokenizer.decode(chunk_tokens))
            if i + self.max_tokens >= len(tokens):
                break
        return chunks

    def process_nodes(self, nodes: List[Dict]) -> List[Dict]:
        """Processes structured code nodes into larger, Nomic-compatible chunks."""
        final_chunks = []
        for node in nodes:
            content = node['content']
            tokens = self.tokenizer.encode(content, add_special_tokens=False)
            token_count = len(tokens)

            if token_count <= self.max_tokens:
                node['token_count'] = token_count
                node['is_partial'] = False
                final_chunks.append(node)
            else:
                final_chunks.extend(self._sliding_window(node, tokens))
        return final_chunks

    def _sliding_window(self, node: Dict, tokens: List[int]) -> List[Dict]:
        """Splits large token arrays into overlapping windows."""
        sub_chunks = []
        step = self.max_tokens - self.overlap
        num_windows = math.ceil(len(tokens) / step)
        
        for i in range(num_windows):
            start = i * step
            end = start + self.max_tokens
            chunk_tokens = tokens[start:end]
            chunk_text = self.tokenizer.decode(chunk_tokens)
            
            sub_chunks.append({
                'name': f"{node.get('name', 'chunk')}_part_{i+1}",
                'type': node.get('type', 'code_block'),
                'content': chunk_text,
                'start_line': node.get('start_line', 0),
                'token_count': len(chunk_tokens),
                'is_partial': True
            })
            if end >= len(tokens):
                break
        return sub_chunks
