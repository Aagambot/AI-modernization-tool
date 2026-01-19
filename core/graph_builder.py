import os
import networkx as nx
import requests
import tree_sitter_python as tspython
from tree_sitter import Language, Parser

class CodeGraphPipeline:
    def __init__(self):
        """
        No repo_root needed; GitHub API provides relative paths automatically.
        """
        self.lang = Language(tspython.language())
        self.parser = Parser(self.lang)
        self.G = nx.MultiDiGraph() 
        self.symbol_table = {} 

    def _get_name(self, node, code_bytes):
        name_node = node.child_by_field_name("name")
        if name_node:
            return code_bytes[name_node.start_byte:name_node.end_byte].decode()
        return None
    
    def pass_1_symbols(self, rel_path, code_bytes):
        """Standardized node IDs using GitHub paths."""
        tree = self.parser.parse(code_bytes)
        self.G.add_node(rel_path, type='file')

        def traverse(node):
            if node.type in ['function_definition', 'class_definition']:
                name = self._get_name(node, code_bytes)
                if name:
                    self.symbol_table[name] = rel_path
                    node_id = f"{rel_path}:{name}"
                    self.G.add_node(node_id, type=node.type, name=name)
                    self.G.add_edge(rel_path, node_id, type='CONTAINS')
            for child in node.children: 
                traverse(child)
        
        traverse(tree.root_node)

    def pass_2_calls(self, rel_path, code_bytes):
        tree = self.parser.parse(code_bytes)

        def traverse(node, current_caller=None):
            if node.type == 'function_definition':
                current_caller = self._get_name(node, code_bytes)
            elif node.type == 'call' and current_caller:
                func_node = node.child_by_field_name('function')
                if func_node:
                    callee_name = code_bytes[func_node.start_byte:func_node.end_byte].decode()
                    if callee_name in self.symbol_table:
                        source_id = f"{rel_path}:{current_caller}"
                        target_rel_path = self.symbol_table[callee_name]
                        target_id = f"{target_rel_path}:{callee_name}"
                        
                        if self.G.has_node(source_id):
                            self.G.add_edge(source_id, target_id, type='CALLS')
            
            for child in node.children: 
                traverse(child, current_caller)
                
        traverse(tree.root_node)

    def process_remote_files(self, remote_file_list):
        """
        remote_file_list: list of {'path': ..., 'download_url': ...}
        """
        contents = {}
        headers = {"Authorization": f"token {os.getenv('GITHUB_TOKEN')}"} if os.getenv('GITHUB_TOKEN') else {}

        # 1. Fetch all bytes into memory
        for f_info in remote_file_list:
            try:
                resp = requests.get(f_info['download_url'], headers=headers)
                if resp.status_code == 200:
                    contents[f_info['path']] = resp.content
            except Exception as e:
                print(f"⚠️ Failed to fetch {f_info['path']}: {e}")
        
        # 2. Pass 1: Symbols
        for rel_path, code in contents.items(): 
            self.pass_1_symbols(rel_path, code)
            
        # 3. Pass 2: Relationships
        for rel_path, code in contents.items(): 
            self.pass_2_calls(rel_path, code)
        
        print(f"✅ Remote Graph built: {self.G.number_of_nodes()} nodes, {self.G.number_of_edges()} edges.")
        return self.G