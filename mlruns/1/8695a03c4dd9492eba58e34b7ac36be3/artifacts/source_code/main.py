import os
import networkx as nx
import time
from pathlib import Path
from scanner import LocalScanner
from graph_builder import CodeGraphPipeline
from storage import VectorStore
from embedder import BGEEmbedder
from chunker import HybridChunker
from chat import ModernizationChat 
from evaluate_pipeline import PipelineEvaluator
from logger import PipelineLogger

def run_modernization_pipeline(repo_path: str, target_subfolder_str: str):
    # --- Initialization ---
    scanner = LocalScanner(repo_path)
    builder = CodeGraphPipeline()
    embedder = BGEEmbedder()
    store = VectorStore()
    chunker = HybridChunker()
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
    nx.write_gexf(builder.G, graph_filename)
    
    if target_chunks:
        print(f"🧠 Embedding {len(target_chunks)} chunks...")
        for chunk in target_chunks:
            chunk['vector'] = embedder.embed_batch([chunk['content']])[0]
        store.save_chunks(target_chunks, mode="overwrite")
    else:
        print("❌ Error: No chunks found.")
        return

    # --- INTEGRATION: Run Evaluation ---
    print("🧪 Indexing complete. Starting Evaluation...")
    chat = ModernizationChat(target_subfolder_str)
    evaluator = PipelineEvaluator(chat)
    
    # Ground Truth for Evaluation
    target_fields = ["customer", "is_return", "grand_total", "posting_date"]
    target_methods = ["validate", "on_submit"]
    
    eval_metrics = evaluator.run_evaluation(target_fields, target_methods)
    evaluator.print_report()

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
        "evaluation_report": "domain_model.json" 
    }
    
    logger.log_run(config, eval_metrics, artifacts)
    print("✅ Full Pipeline Run, Evaluation, and Versioning Complete.")

if __name__ == "__main__":
    REPO_ROOT = r"C:/Users/Aagam/OneDrive/Desktop/erpnext"
    TARGET_DIR = r"C:/Users/Aagam/OneDrive/Desktop/erpnext/erpnext/accounts/doctype/sales_invoice"
    run_modernization_pipeline(REPO_ROOT, TARGET_DIR)