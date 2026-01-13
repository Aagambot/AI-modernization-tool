import os
import networkx as nx
from scanner import LocalScanner
from graph_builder import CodeGraphPipeline
from storage import VectorStore
from embedder import BGEEmbedder
from chunker import HybridChunker
from pathlib import Path

def run_modernization_pipeline(repo_path: str, target_subfolder_str: str):
    scanner = LocalScanner(repo_path)
    builder = CodeGraphPipeline()
    embedder = BGEEmbedder()
    store = VectorStore()
    chunker = HybridChunker()

    # Convert strings to Path objects for safe Windows handling
    root = Path(repo_path).resolve()
    target_path = Path(target_subfolder_str).resolve()

    print(f"🚀 Scanning repository: {root}")
    all_files = scanner.get_files()
    
    # Pass 1: Global Symbols (All files)
    print("🔍 Pass 1: Building Global Symbol Table...")
    for f_path in all_files:
        try:
            with open(f_path, 'rb') as f:
                builder.pass_1_symbols(f_path, f.read())
        except Exception:
            continue

    # Filter: Only files inside the target folder
    target_files = []
    for f in all_files:
        if Path(f).resolve().is_relative_to(target_path):
            target_files.append(f)

    print(f"🔗 Pass 2: Found {len(target_files)} files in target. Building deep relationships...")
    
    target_chunks = []
    for f_path in target_files:
        try:
            with open(f_path, 'rb') as f:
                content_bytes = f.read()
                # Deep AST analysis for graph edges
                builder.pass_2_calls(f_path, content_bytes)
                
                content_str = content_bytes.decode('utf-8', errors='ignore')
                file_chunks = chunker.split_text(content_str)
                for c in file_chunks:
                    target_chunks.append({
                        "content": c,
                        "file_path": f_path,
                        "name": os.path.basename(f_path)
                    })
        except Exception as e:
            print(f"⚠️ Error processing {f_path}: {e}")

    # Save Graph
    nx.write_gexf(builder.G, "sales_invoice_graph.gexf")
    
    # Vector Indexing
    if target_chunks:
        print(f"🧠 Pass 3: Embedding {len(target_chunks)} chunks...")
        for chunk in target_chunks:
            chunk['vector'] = embedder.embed_batch([chunk['content']])[0]
        store.save_chunks(target_chunks, mode="overwrite")
        print("✅ Pipeline complete.")
    else:
        print(f"❌ Error: No files found in {target_path}")

if __name__ == "__main__":
    # Updated paths for your specific Windows setup
    REPO_ROOT = r"C:/Users/Aagam/OneDrive/Desktop/erpnext"
    TARGET_DIR = r"C:/Users/Aagam/OneDrive/Desktop/erpnext/erpnext/accounts/doctype/sales_invoice"
    
    run_modernization_pipeline(REPO_ROOT, TARGET_DIR)
