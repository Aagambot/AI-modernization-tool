import tree_sitter_python as tspython
from tree_sitter import Language, Parser

# ERPNext lifecycle hooks to prioritize
ERPNEXT_HOOKS = {
    'validate', 'before_validate', 'after_validate',
    'on_submit', 'before_submit', 'on_cancel',
    'on_update', 'after_insert', 'before_save',
    'on_trash', 'after_delete'
}

class LocalGraphParser:
    def __init__(self):
        self.lang = Language(tspython.language())
        self.parser = Parser(self.lang)

    def parse_local_file(self, file_path: str):
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
            
            tree = self.parser.parse(content)
            # Pass file_path down to create unique IDs
            return self._extract_data(tree.root_node, content, file_path)
        except Exception as e:
            print(f"❌ Error parsing {file_path}: {e}")
            return None

    def _extract_data(self, root_node, content, file_path):
        """Traverses AST to create structured chunks."""
        chunks = []

        def get_text(node):
            return content[node.start_byte:node.end_byte].decode('utf8')

        def traverse(node, current_class=None):
            # 1. Extract Definitions with full metadata
            if node.type in ["function_definition", "class_definition"]:
                name_node = node.child_by_field_name("name")
                if name_node:
                    symbol_name = get_text(name_node)
                    
                    # Identify if it's an ERPNext hook
                    hook_type = symbol_name if symbol_name in ERPNEXT_HOOKS else None
                    
                    chunks.append({
                        "id": f"{file_path}:{symbol_name}", # Unique ID
                        "content": get_text(node),           # Full code block
                        "file_path": file_path,
                        "symbol_name": symbol_name,
                        "symbol_type": node.type,
                        "hook_type": hook_type,
                        "start_line": node.start_point[0] + 1,
                        "end_line": node.end_point[0] + 1
                    })
                    
                    if node.type == "class_definition":
                        current_class = symbol_name


            for child in node.children:
                traverse(child, current_class)

        traverse(root_node)
        return chunks