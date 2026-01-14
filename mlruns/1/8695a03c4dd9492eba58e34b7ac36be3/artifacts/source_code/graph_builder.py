import networkx as nx
import tree_sitter_python as tspython
from tree_sitter import Language, Parser
from pathlib import Path

class CodeGraphPipeline:
    def __init__(self):
        self.lang = Language(tspython.language())
        self.parser = Parser(self.lang)
        self.G = nx.DiGraph()
        self.symbol_table = {}  # Maps "FunctionName" -> "file_path"

    def _get_name(self, node, code_bytes):
        """Helper to extract identifier name from a node."""
        name_node = node.child_by_field_name("name")
        if name_node:
            return code_bytes[name_node.start_byte:name_node.end_byte].decode()
        return None
    
    def pass_1_symbols(self, file_path, code_bytes):
        """Extracts definitions to populate the global symbol table."""
        tree = self.parser.parse(code_bytes)
        self.G.add_node(file_path, type='file')

        def traverse(node):
            if node.type in ['function_definition', 'class_definition']:
                name = self._get_name(node, code_bytes)
                if name:
                    # Global symbol resolution: Map name to its source file
                    self.symbol_table[name] = file_path
                    node_id = f"{file_path}:{name}"
                    self.G.add_node(node_id, type=node.type, name=name)
                    self.G.add_edge(file_path, node_id, type='CONTAINS')
            for child in node.children: traverse(child)
        traverse(tree.root_node)

    def pass_2_calls(self, file_path, code_bytes):
        """Extracts calls and links them to the symbol table."""
        tree = self.parser.parse(code_bytes)

        def traverse(node, current_caller=None):
            if node.type == 'function_definition':
                current_caller = self._get_name(node, code_bytes)

            elif node.type == 'call' and current_caller:
                # Extract the name of the function being called
                func_node = node.child_by_field_name('function')
                if func_node:
                    callee_name = code_bytes[func_node.start_byte:func_node.end_byte].decode()
                    # Resolve call: Link current function to its callee
                    if callee_name in self.symbol_table:
                        source = f"{file_path}:{current_caller}"
                        target = f"{self.symbol_table[callee_name]}:{callee_name}"
                        self.G.add_edge(source, target, type='CALLS')
            
            for child in node.children: traverse(child, current_caller)
        traverse(tree.root_node)

    def process_files(self, file_list):
        """Orchestrates the two-pass graph construction."""
        contents = {f: open(f, 'rb').read() for f in file_list}
        
        for f, code in contents.items(): self.pass_1_symbols(f, code)
        for f, code in contents.items(): self.pass_2_relationships(f, code)
        
        print(f"Graph built: {self.G.number_of_nodes()} nodes, {self.G.number_of_edges()} edges.")
        return self.G
