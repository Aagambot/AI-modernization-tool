from scanner import RemoteScanner
from parser import ASTParser
from chunker import HybridChunker
from embedder import BGEEmbedder
from storage import VectorStore
import requests

# 1. Setup Classes
scanner = RemoteScanner("https://github.com/frappe/erpnext/tree/develop/erpnext/accounts/doctype/sales_invoice")
parser = ASTParser()
chunker = HybridChunker()
embedder = BGEEmbedder()
store = VectorStore()

# 2. Execute Sequential Pipeline
print("Starting Pipeline...")

# Step 1: Discover
files = scanner.get_file_list()

all_final_chunks = []
for f in files:
    # Step 2: Fetch & Parse
    code = requests.get(f['download_url']).text
    nodes = parser.parse_code(code, f['extension'])
    
    # Step 3: Chunk (ensure token safety)
    chunks = chunker.process_nodes(nodes)
    
    # Add file path to metadata for each chunk
    for c in chunks:
        c['file_path'] = f['path']
        
    all_final_chunks.extend(chunks)

# Step 4: Embed (Batch)
embedded_data = embedder.embed_chunks(all_final_chunks)

# Step 5: Store
store.save_chunks(embedded_data)

print("\n🎉 Pipeline Complete! Your code is now searchable.")