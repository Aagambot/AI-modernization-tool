import tree_sitter_python as tspython
from tree_sitter import Language, Parser, Query

# 1. Setup (Modern API)
PY_LANG = Language(tspython.language())
parser = Parser(PY_LANG)
# This query looks for function definitions and captures their 'name'
QUERY = Query(PY_LANG, "(function_definition name: (identifier) @name) @func")

def extract_functions_ast(code: str) -> list[dict]:
    tree = parser.parse(bytes(code, "utf8"))
    functions = []
    
    # 2. Execute Query
    captures = QUERY.c(tree.root_node)
    
    # 3. Process Captures (Modern tree-sitter returns a dict of {tag: [nodes]})
    # We iterate through the '@func' nodes to get the full function body
    for node in captures.get("func", []):
        # Find the specific 'name' node inside this function
        name = "unknown"
        for n in captures.get("name", []):
            if n.start_byte >= node.start_byte and n.end_byte <= node.end_byte:
                name = code[n.start_byte:n.end_byte]
                break

        functions.append({
            'name': name,
            'start_line': node.start_point[0],
            'code': code[node.start_byte:node.end_byte]
        })
    return functions

# --- TEST ---
if __name__ == "__main__":
    example = "def greet():\n    print('hello')\n\ndef add(a, b): return a + b"
    for f in extract_functions_ast(example):
        print(f"Name: {f['name']} | Line: {f['start_line']}")