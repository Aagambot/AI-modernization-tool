from transformers import AutoTokenizer
import math
from typing import List, Dict

class HybridChunker:
    def __init__(self, model_name: str = "nomic-embed-text", max_tokens: int = 500, overlap: int = 50):
        """
        Refactored Chunker optimized for BERT-based embedding limits.
        Ensures chunks never exceed the 512-token boundary that triggers indexing errors.
        """
        self.tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased")
        self.max_tokens = max_tokens
        self.overlap = overlap

    def split_text(self, text: str) -> List[str]:
        """
        Processes raw text and returns a list of chunks within the token limit.
        Used to break down large files (like the 18,000+ token SalesInvoice) before embedding.
        """
        tokens = self.tokenizer.encode(text, add_special_tokens=False)
        if len(tokens) <= self.max_tokens:
            return [text]

        chunks = []
        step = max(1, self.max_tokens - self.overlap)
        for i in range(0, len(tokens), step):
            chunk_tokens = tokens[i : i + self.max_tokens]
            chunks.append(self.tokenizer.decode(chunk_tokens))
            if i + self.max_tokens >= len(tokens):
                break
        return chunks

    def process_nodes(self, nodes: List[Dict]) -> List[Dict]:
        """Processes structured code nodes into chunks compatible with the vector store."""
        final_chunks = []
        for node in nodes:
            content = node['content']
            tokens = self.tokenizer.encode(content, add_special_tokens=False)
            token_count = len(tokens)

            # Check if original node content fits within limits
            if token_count <= self.max_tokens:
                node['token_count'] = token_count
                node['is_partial'] = False
                final_chunks.append(node)
            else:
                # Use sliding window for oversized code blocks
                final_chunks.extend(self._sliding_window(node, tokens))
        return final_chunks

    def _sliding_window(self, node: Dict, tokens: List[int]) -> List[Dict]:
        """Splits large token arrays into overlapping windows for partial indexing."""
        sub_chunks = []
        step = max(1, self.max_tokens - self.overlap)
        
        for i, start in enumerate(range(0, len(tokens), step)):
            end = start + self.max_tokens
            chunk_tokens = tokens[start:end]
            chunk_text = self.tokenizer.decode(chunk_tokens)
            
            sub_chunks.append({
                'name': f"{node.get('name', 'chunk')}_part_{i+1}",
                'type': node.get('type', 'code_block'),
                'content': chunk_text,
                'file_path': node.get('file_path', ''),
                'start_line': node.get('start_line', 0),
                'token_count': len(chunk_tokens),
                'is_partial': True
            })
            if end >= len(tokens):
                break
        return sub_chunks