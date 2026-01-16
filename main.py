import os
import networkx as nx
import time
from pathlib import Path
from core.scanner import LocalScanner
from core.graph_builder import CodeGraphPipeline
from data.storage import VectorStore
from engine.embedder import BGEEmbedder
from engine.chunker import HybridChunker
from utils.logger import PipelineLogger
from tests.verify_retrieval import RetrievalEvaluator
from utils.graph_to_mermaid import export_folder_to_mermaid

def run_modernization_pipeline(repo_path: str, target_subfolder_str: str):
    # --- Initialization ---
    scanner = LocalScanner(repo_path)
    builder = CodeGraphPipeline(repo_path)
    embedder = BGEEmbedder()
    store = VectorStore()
    chunker = HybridChunker()
    evaluator = RetrievalEvaluator()
    logger = PipelineLogger()
    
    root = Path(repo_path).resolve()
    target_path = Path(target_subfolder_str).resolve()
    entity_name = target_path.name.replace("_", " ").title().replace(" ", "")

    print(f"🚀 Scanning repository: {root}")
    all_files = scanner.get_files()
    
    # --- PASS 1: Global Symbols ---
    for f_path in all_files:
        try:
            with open(f_path, 'rb') as f:
                builder.pass_1_symbols(f_path, f.read())
        except Exception: continue

    # --- PASS 2: Target File Analysis ---
    target_files = [f for f in all_files if Path(f).resolve().is_relative_to(target_path)]
    print(f"🔗 Found {len(target_files)} files in target. Building relationships...")
    
    target_chunks = []
    for f_path in target_files:
        try:
            with open(f_path, 'rb') as f:
                content_bytes = f.read()
                builder.pass_2_calls(f_path, content_bytes)
                
                content_str = content_bytes.decode('utf-8', errors='ignore')
                file_chunks = chunker.split_text(content_str)
                for c in file_chunks:
                    target_chunks.append({
                        "content": c, "file_path": f_path, "name": os.path.basename(f_path)
                    })
        except Exception as e:
            print(f"⚠️ Error processing {f_path}: {e}")

    # --- PASS 3: Vector Indexing ---

    graph_filename = f"{target_path.name}_graph.gexf"
    mermaid_filename = f"{target_path.name}_flow.md"
    nx.write_gexf(builder.G, graph_filename)
    graph_path = store.save_graph(builder.G, entity_name)
    print(f"📊 Graph persisted at: {graph_path}")

    #creating mermaid diagram
    export_folder_to_mermaid(graph_filename, folder_name=entity_name, output_file=mermaid_filename)
    print(f"🗂️ Graph saved to {graph_filename} and {mermaid_filename}")

    if target_chunks:
        # Standardize paths in chunks to match Graph Node IDs
        for chunk in target_chunks:
            chunk['file_path'] = os.path.relpath(chunk['file_path'], repo_path).replace('\\', '/')
            chunk['vector'] = embedder.embed_batch([chunk['content']])[0]
        store.save_chunks(target_chunks, mode="overwrite")
    else:
        print("❌ Error: No chunks found.")
        return
    
    eval_results = evaluator.run_benchmark("golden_dataset.json")   
    # --- INTEGRATION: Logging & Versioning ---
    config = {
        "entity": entity_name,
        "folder_path": target_subfolder_str,
        "chunk_size": 2048, 
        "embedding_model": "nomic-embed-text",
        "llm_model": "gemini-2.5-flash"
    }
    
    artifacts = {
        "vector_db": "./code_index_db",
        "graph_file": graph_filename,
        "evaluation_report": "domain_model.json" ,
        "mermaid_diagram": mermaid_filename,
        "graph_file":graph_path
    }
    metrics = {
        "hit_rate_at_5": eval_results.get("hit_rate", 0),
        "mrr": eval_results.get("mrr", 0)
    }
    logger.log_run(config ,metrics,artifacts)
    print("✅ Full Pipeline Run and Versioning Complete.")

if __name__ == "__main__":
    REPO_ROOT = r"C:/Users/Aagam/OneDrive/Desktop/erpnext"
    TARGET_DIR = r"C:/Users/Aagam/OneDrive/Desktop/erpnext/erpnext/accounts/doctype/sales_invoice"
    run_modernization_pipeline(REPO_ROOT, TARGET_DIR)