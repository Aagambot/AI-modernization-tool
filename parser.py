import tree_sitter_python as tspython
from tree_sitter import Language, Parser

class GraphParser:
    def __init__(self):
        self.lang = Language(tspython.language())
        self.parser = Parser(self.lang)

    def extract_nodes_and_edges(self, file_path: str):
        with open(file_path, "rb") as f:
            code = f.read()
        
        tree = self.parser.parse(code)
        # Using native tree-sitter node types for robust extraction
        data = {"definitions": [], "calls": []}

        def traverse(node, parent_class=None):
            # Capture class and function definitions
            if node.type in ["class_definition", "function_definition"]:
                name_node = node.child_by_field_name("name")
                if name_node:
                    name = code[name_node.start_byte:name_node.end_byte].decode()
                    data["definitions"].append({
                        "name": name, 
                        "type": node.type,
                        "parent": parent_class
                    })
                    # Pass class context to nested methods
                    current_class = name if node.type == "class_definition" else parent_class
                    for child in node.children:
                        traverse(child, current_class)
                    return

            # Capture function/method calls
            if node.type == "call":
                func_node = node.child_by_field_name("function")
                if func_node:
                    callee = code[func_node.start_byte:func_node.end_byte].decode()
                    data["calls"].append(callee)

            for child in node.children:
                traverse(child, parent_class)

        traverse(tree.root_node)
        return data