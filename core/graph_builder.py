import os
import networkx as nx
import tree_sitter_python as tspython
from tree_sitter import Language, Parser
from pathlib import Path

class CodeGraphPipeline:
    def __init__(self, repo_root):
        """
        Initialize with repo_root to enable relative path normalization.
        """
        self.repo_root = os.path.abspath(repo_root)
        self.lang = Language(tspython.language())
        self.parser = Parser(self.lang)
        
        self.G = nx.MultiDiGraph() 
        self.symbol_table = {} 
    def _normalize_path(self, absolute_path):
        """
        Converts absolute system paths to standardized relative paths.
        This acts as a 'Primary Key' for both the Graph and Vector DB.
        """
        return os.path.relpath(absolute_path, self.repo_root).replace('\\', '/')

    def _get_name(self, node, code_bytes):
        """Helper to extract identifier name from a node."""
        name_node = node.child_by_field_name("name")
        if name_node:
            return code_bytes[name_node.start_byte:name_node.end_byte].decode()
        return None
    
    def pass_1_symbols(self, file_path, code_bytes):
        """Extracts definitions using relative paths for standardized node IDs."""
        rel_path = self._normalize_path(file_path)
        tree = self.parser.parse(code_bytes)
        
        # Add the file node using its relative path
        self.G.add_node(rel_path, type='file')

        def traverse(node):
            if node.type in ['function_definition', 'class_definition']:
                name = self._get_name(node, code_bytes)
                if name:
                    # Map name to its relative source file for global resolution
                    self.symbol_table[name] = rel_path
                    node_id = f"{rel_path}:{name}"
                    self.G.add_node(node_id, type=node.type, name=name)
                    self.G.add_edge(rel_path, node_id, type='CONTAINS')
            for child in node.children: 
                traverse(child)
        
        traverse(tree.root_node)

    def pass_2_calls(self, file_path, code_bytes):
        """Links function calls to their definitions across the codebase."""
        source_rel_path = self._normalize_path(file_path)
        tree = self.parser.parse(code_bytes)

        def traverse(node, current_caller=None):
            if node.type == 'function_definition':
                current_caller = self._get_name(node, code_bytes)

            elif node.type == 'call' and current_caller:
                func_node = node.child_by_field_name('function')
                if func_node:
                    callee_name = code_bytes[func_node.start_byte:func_node.end_byte].decode()
                    # Resolve call: Link using standardized relative paths
                    if callee_name in self.symbol_table:
                        source_id = f"{source_rel_path}:{current_caller}"
                        target_rel_path = self.symbol_table[callee_name]
                        target_id = f"{target_rel_path}:{callee_name}"
                        
                        # Verify source node exists before adding edge
                        if self.G.has_node(source_id):
                            self.G.add_edge(source_id, target_id, type='CALLS')
            
            for child in node.children: 
                traverse(child, current_caller)
                
        traverse(tree.root_node)

    def process_files(self, file_list):
        """Orchestrates the two-pass graph construction with standardized paths."""
        contents = {}
        for f in file_list:
            try:
                with open(f, 'rb') as file:
                    contents[f] = file.read()
            except Exception as e:
                print(f"⚠️ Warning: Could not read {f}: {e}")
        
        # Pass 1: Build the symbol table
        for f, code in contents.items(): 
            self.pass_1_symbols(f, code)
            
        # Pass 2: Connect the calls based on the symbol table
        for f, code in contents.items(): 
            self.pass_2_calls(f, code)
        
        print(f"✅ Graph built: {self.G.number_of_nodes()} nodes, {self.G.number_of_edges()} edges.")
        return self.G