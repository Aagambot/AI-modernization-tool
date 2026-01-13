import tree_sitter_python as tspython
from tree_sitter import Language, Parser

class LocalGraphParser:
    def __init__(self):
        # Precompiled Python grammar
        self.lang = Language(tspython.language())
        self.parser = Parser(self.lang)

    def parse_local_file(self, file_path: str):
        """Reads a local file and extracts its AST structure."""
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
            
            tree = self.parser.parse(content)
            return self._extract_data(tree.root_node, content)
        except Exception as e:
            print(f"❌ Error parsing {file_path}: {e}")
            return None

    def _extract_data(self, root_node, content):
        """Traverses the AST to find definitions and calls."""
        data = {"definitions": [], "calls": []}

        def get_text(node):
            return content[node.start_byte:node.end_byte].decode('utf8')

        def traverse(node):
            # 1. Extract function and class definitions
            if node.type in ["function_definition", "class_definition"]:
                name_node = node.child_by_field_name("name")
                if name_node:
                    data["definitions"].append({
                        "name": get_text(name_node),
                        "type": node.type,
                        "start_line": node.start_point[0] + 1
                    })

            # 2. Extract calls (handles self.method() and regular calls)
            if node.type == "call":
                func_node = node.child_by_field_name("function")
                if func_node:
                    # If it's an attribute like 'self.validate', get the 'validate' part
                    if func_node.type == "attribute":
                        attr_node = func_node.child_by_field_name("attribute")
                        if attr_node:
                            data["calls"].append(get_text(attr_node))
                    else:
                        data["calls"].append(get_text(func_node))

            for child in node.children:
                traverse(child)

        traverse(root_node)
        return data