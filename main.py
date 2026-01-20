import os
import json
import asyncio
import networkx as nx
from engine.utils import parse_github_url
from core.scanner import GitHubScanner
from core.graph_builder import CodeGraphPipeline
from data.storage import VectorStore
from engine.embedder import BGEEmbedder
from engine.chunker import HybridChunker
from utils.logger import PipelineLogger
from tests.verify_retrieval import RetrievalEvaluator
from utils.graph_to_mermaid import export_folder_to_mermaid

async def run_modernization_pipeline(github_url: str):
    # --- Phase 1: URL Parsing ---
    repo_info = parse_github_url(github_url)
    if not repo_info:
        print("❌ Invalid GitHub URL.")
        return

    entity_name = repo_info['path'].split('/')[-1].replace("_", " ").title().replace(" ", "")
    
    # --- Initialization ---
    scanner = GitHubScanner()
    builder = CodeGraphPipeline()
    embedder = BGEEmbedder()
    store = VectorStore()
    chunker = HybridChunker()
    evaluator = RetrievalEvaluator()
    logger = PipelineLogger()

    print(f"🚀 Initializing Remote Scan: {repo_info['owner']}/{repo_info['repo']}")
    
    # --- Phase 2: Remote Scanning (No local cloning) ---
    remote_files = scanner.scan_remote_folder(
        repo_info['owner'], 
        repo_info['repo'], 
        repo_info['path'], 
        repo_info['branch']
    )

    # --- Phase 3: Building the Graph & Chunks in RAM ---
    print(f"🔗 Processing {len(remote_files)} files from GitHub...")
    
    # Fetch content and build graph symbols (Pass 1 & 2)
    builder.process_remote_files(remote_files)
    
    target_chunks = []
    for f_info in remote_files:
        try:
            import requests
            content_bytes = requests.get(f_info['download_url']).content
            content_str = content_bytes.decode('utf-8', errors='ignore')
            
            file_chunks = chunker.split_text(content_str)
            for c in file_chunks:
                target_chunks.append({
                    "content": c, 
                    "file_path": f_info['path'], 
                    "name": f_info['path'].split('/')[-1]
                })
        except Exception as e:
            print(f"⚠️ Error processing {f_info['path']}: {e}")
    
    # --- Persisting Artifacts ---
    graph_filename = f"{entity_name}_graph.gexf"
    mermaid_filename = f"{entity_name}_flow.md"
    
    nx.write_gexf(builder.G, graph_filename)
    graph_path = store.save_graph(builder.G, entity_name)
    
    # Creating mermaid diagram
    export_folder_to_mermaid(graph_filename, folder_name=entity_name, output_file=mermaid_filename)
    print(f"📊 Graph and Flowchart saved remotely.")

    # --- Vector Indexing ---
    if target_chunks:
        print(f"🧬 Embedding {len(target_chunks)} chunks...")
        for chunk in target_chunks:
            chunk['vector'] = embedder.embed_batch([chunk['content']])[0]
        
        store.save_chunks(target_chunks, mode="overwrite")
    else:
        print("❌ Error: No chunks found.")
        return
    
    # --- Evaluation (Updated for LLM-as-a-Judge) ---
    print("🧠 Starting Automated Evaluation...")
    eval_results = await evaluator.run_benchmark("golden_dataset.json") 
    
    metrics = {
        "hit_rate_at_5": eval_results.get("hit_rate", 0),
        "mrr": eval_results.get("mrr", 0),
        "avg_accuracy": eval_results.get("avg_accuracy", 0),
        "avg_completeness": eval_results.get("avg_completeness", 0)
    }
        
    # --- Artifact Paths ---
    artifact_paths = {
        "graph": graph_path,
        "mermaid": mermaid_filename,
        "detailed_results": "evaluation_report.json"
    }

    # Save detailed results for MLflow logging
    with open("evaluation_report.json", "w") as f:
        json.dump(eval_results.get("detailed_results", []), f, indent=4)
    
    # Log everything to MLflow
    logger.log_run(
        {"entity": entity_name, "source": "GitHub", "chunk_size": 500}, 
        metrics, 
        artifact_paths
    )
    
    print("✅ Remote Pipeline Complete.")

if __name__ == "__main__":
    GITHUB_URL = "https://github.com/frappe/erpnext/tree/develop/erpnext/accounts/doctype/sales_invoice"
    asyncio.run(run_modernization_pipeline(GITHUB_URL))