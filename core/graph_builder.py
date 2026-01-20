import os
import networkx as nx
import requests
import tree_sitter_python as tspython
from tree_sitter import Language, Parser

class CodeGraphPipeline:
    def __init__(self):
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
        """Phase 1: Build a granular symbol table (File -> Class -> Method)."""
        tree = self.parser.parse(code_bytes)
        self.G.add_node(rel_path, type='file')

        def traverse(node, current_class=None):
            if node.type == 'class_definition':
                class_name = self._get_name(node, code_bytes)
                if class_name:
                    node_id = f"{rel_path}:{class_name}"
                    self.G.add_node(node_id, type='class', name=class_name)
                    self.G.add_edge(rel_path, node_id, type='CONTAINS')
                    self.symbol_table[class_name] = node_id
                    current_class = class_name

            elif node.type == 'function_definition':
                func_name = self._get_name(node, code_bytes)
                if func_name:
                    # Create a hierarchical ID
                    prefix = f"{rel_path}:{current_class}" if current_class else rel_path
                    node_id = f"{prefix}:{func_name}"
                    safe_parent = current_class if current_class is not None else ""
                    
                    self.G.add_node(node_id, type='function', name=func_name, parent_class=safe_parent)
                    parent_id = f"{rel_path}:{current_class}" if current_class else rel_path
                    self.G.add_edge(parent_id, node_id, type='CONTAINS')
                    
                    # Map the bare name to the full ID for resolution in Pass 2
                    self.symbol_table[func_name] = node_id

            for child in node.children: 
                traverse(child, current_class)
        
        traverse(tree.root_node)

    def pass_2_calls(self, rel_path, code_bytes):
        """Phase 2: Link specific function calls to their definitions."""
        tree = self.parser.parse(code_bytes)

        def traverse(node, current_caller_id=None):
            if node.type == 'function_definition':
                func_name = self._get_name(node, code_bytes)
                # Reconstruct the caller ID based on Pass 1 logic
                # We search the graph to find the node we created in Pass 1
                for n, attr in self.G.nodes(data=True):
                    if attr.get('type') == 'function' and n.startswith(rel_path) and attr.get('name') == func_name:
                        current_caller_id = n
                        break

            elif node.type == 'call' and current_caller_id:
                func_node = node.child_by_field_name('function')
                if func_node:
                    raw_call = code_bytes[func_node.start_byte:func_node.end_byte].decode()
                    # Clean 'self.method' or 'cls.method' to just 'method'
                    callee_name = raw_call.split('.')[-1]
                    
                    if callee_name in self.symbol_table:
                        target_id = self.symbol_table[callee_name]
                        if self.G.has_node(current_caller_id) and self.G.has_node(target_id):
                            self.G.add_edge(current_caller_id, target_id, type='CALLS')
            
            for child in node.children: 
                traverse(child, current_caller_id)
                
        traverse(tree.root_node)

    def process_remote_files(self, remote_file_list):
        contents = {}
        headers = {"Authorization": f"token {os.getenv('GITHUB_TOKEN')}"} if os.getenv('GITHUB_TOKEN') else {}

        for f_info in remote_file_list:
            if not f_info['path'].endswith('.py'): continue
            try:
                resp = requests.get(f_info['download_url'], headers=headers)
                if resp.status_code == 200:
                    contents[f_info['path']] = resp.content
            except Exception as e:
                print(f"⚠️ Failed to fetch {f_info['path']}: {e}")
        
        for rel_path, code in contents.items(): 
            self.pass_1_symbols(rel_path, code)
            
        for rel_path, code in contents.items(): 
            self.pass_2_calls(rel_path, code)
        
        print(f"✅ Enhanced Graph built: {self.G.number_of_nodes()} nodes, {self.G.number_of_edges()} edges.")
        return self.G