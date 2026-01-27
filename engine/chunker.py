import tree_sitter_python as tspython
from tree_sitter import Language, Parser
from typing import List, Dict, Any
from dataclasses import dataclass

# ERPNext lifecycle hooks to prioritize
ERPNEXT_HOOKS = {
    'validate', 'before_validate', 'after_validate',
    'on_submit', 'before_submit', 'on_cancel',
    'on_update', 'after_insert', 'before_save',
    'on_trash', 'after_delete'
}

class HybridChunker:
    def __init__(self):
        """
        AST-based chunker for ERPNext.
        Replaces token-based sliding windows with structural code extraction.
        """
        self.PY_LANGUAGE = Language(tspython.language())
        self.parser = Parser(self.PY_LANGUAGE)

    def chunk_erpnext_file(self, content: str, file_path: str) -> List[Dict[str, Any]]:
        """
        Main entry point for AST-based chunking.
        """
        tree = self.parser.parse(bytes(content, "utf8"))
        chunks = []
        
        # Traverse the AST to find classes and functions
        self._traverse_tree(tree.root_node, content, file_path, chunks)
        return chunks

    def _traverse_tree(self, node: Any, code: str, file_path: str, chunks: List[Dict]):
        """
        Recursively extracts significant symbols (classes/methods).
        """
        # Extract Classes (DocType controllers)
        if node.type == 'class_definition':
            chunks.append(self._create_chunk(node, code, file_path, "class"))

        # Extract Functions/Methods (Business Logic)
        elif node.type == 'function_definition':
            symbol_name = self._get_node_name(node, code)
            symbol_type = "method" if node.parent and node.parent.type == 'block' and \
                          node.parent.parent and node.parent.parent.type == 'class_definition' \
                          else "function"
            
            chunk = self._create_chunk(node, code, file_path, symbol_type)
            
            # Identify if it's an ERPNext hook
            if symbol_name in ERPNEXT_HOOKS:
                chunk['hook_type'] = symbol_name
            
            chunks.append(chunk)

        # Continue traversal for child nodes
        for child in node.children:
            self._traverse_tree(child, code, file_path, chunks)

    def _create_chunk(self, node: Any, code: str, file_path: str, symbol_type: str) -> Dict:
        """
        Formats a node into the CodeChunk schema.
        """
        start_line = node.start_point[0] + 1
        end_line = node.end_point[0] + 1
        symbol_name = self._get_node_name(node, code)
        
        # Extract source code for the specific node
        node_code = code.encode('utf8')[node.start_byte:node.end_byte].decode('utf8')

        return {
            "id": f"{file_path}:{symbol_name}",
            "file_path": file_path,
            "symbol_name": symbol_name,
            "symbol_type": symbol_type,
            "code": node_code,
            "start_line": start_line,
            "end_line": end_line,
            "hook_type": None
        }

    def _get_node_name(self, node: Any, code: str) -> str:
        """Helper to extract the name identifier from a node."""
        for child in node.children:
            if child.type == 'identifier':
                return code.encode('utf8')[child.start_byte:child.end_byte].decode('utf8')
        return "unknown"