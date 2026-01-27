import os
import json
import asyncio
import hashlib
import networkx as nx
import aiohttp
from engine.utils import parse_github_url
from core.scanner import GitHubScanner
from core.graph_builder import CodeGraphPipeline
from data.storage import VectorStore
from engine.embedder import BGEEmbedder
from engine.chunker import HybridChunker
from utils.logger import PipelineLogger
from tests.verify_retrieval import RetrievalEvaluator
from utils.graph_to_mermaid import export_folder_to_mermaid

def get_content_hash(content: str) -> str:
    """Generates a SHA-256 hash to detect file changes."""
    return hashlib.sha256(content.encode('utf-8')).hexdigest()

async def fetch_and_process(session, f_info, chunker, existing_hashes, builder):
    """
    Aligned with Phase 2: AST-based extraction and metadata mapping.
    """
    try:
        async with session.get(f_info['download_url']) as response:
            content = await response.text(errors='ignore')
            new_hash = get_content_hash(content)
            
            # 1. Delta Check: Skip if unchanged
            if existing_hashes.get(f_info['path']) == new_hash:
                return None, new_hash 

            # 2. Structural Symbol Extraction (Pass 1 of Graph)
            builder.process_single_file(f_info, content)
            
            # 3. AST-based Chunking
            raw_chunks = chunker.chunk_erpnext_file(content, f_info['path'])
            
            return raw_chunks, new_hash
    except Exception as e:
        print(f"⚠️ Error: {f_info['path']}: {e}")
        return [], None

async def run_modernization_pipeline(github_url: str):
    repo_info = parse_github_url(github_url)
    if not repo_info: return

    entity_name = repo_info['path'].split('/')[-1].replace("_", "").title()
    
    # Initialization
    scanner, builder, embedder = GitHubScanner(), CodeGraphPipeline(), BGEEmbedder()
    store, logger = VectorStore(), PipelineLogger()
    chunker = HybridChunker()
    evaluator = RetrievalEvaluator()

    # Delta Indexing: Load state
    existing_hashes = store.load_hashes()
    new_hashes = {}
    all_new_chunks = []

    remote_files = scanner.scan_remote_folder(
        repo_info['owner'], repo_info['repo'], repo_info['path'], repo_info['branch']
    )

    print(f"🔗 Processing {len(remote_files)} files...")
    async with aiohttp.ClientSession() as session:
        # Create tasks for all remote files
        tasks = [fetch_and_process(session, f, chunker, existing_hashes, builder) for f in remote_files]
        results = await asyncio.gather(*tasks)
        
        for i, (chunks, f_hash) in enumerate(results):
            path = remote_files[i]['path']
            # If chunks is None, file was unchanged (Delta Indexing)
            if chunks is None:
                new_hashes[path] = existing_hashes[path]
                continue
            
            # If we have new AST chunks, add them to the batch
            if chunks:
                all_new_chunks.extend(chunks)
                new_hashes[path] = f_hash
                # store.delete_file_vectors(path)
    
    if all_new_chunks:
        print(f"🧬 Embedding {len(all_new_chunks)} AST-based chunks...")
        batch_size = 64
        for i in range(0, len(all_new_chunks), batch_size):
            batch = all_new_chunks[i : i + batch_size]
            texts = [c['code'] for c in batch]
            
            # Use prefixing for high-precision document indexing
            embeddings = await asyncio.to_thread(embedder.embed_batch, texts, is_query=False)
            
            for j, emb in enumerate(embeddings):
                # Map to the VectorStore schema
                batch[j]['vector'] = emb
                batch[j]['content'] = batch[j].pop('code') 
        
        # Save to LanceDB with the expanded metadata
        store.save_chunks(all_new_chunks)
    
    store.save_hashes(new_hashes)

    # Persist Artifacts
    graph_filename = f"{entity_name}_graph.gexf"
    nx.write_gexf(builder.G, graph_filename)
    store.save_graph(builder.G, entity_name)
    export_folder_to_mermaid(graph_filename, folder_name=entity_name, output_file=f"{entity_name}_flow.md")

    # Evaluation
    print("🧠 Starting Evaluation...")
    eval_results = await evaluator.run_benchmark("golden_dataset.json") 
    detailed_data = eval_results.get("detailed_results", [])

    report_path = "evaluation_report.json"
    with open(report_path, "w") as f:
        json.dump(detailed_data, f, indent=4)

    # MLflow Logging
    logger.log_run(
    config={"entity": entity_name, "chunk_size": 500}, 
    metrics={"accuracy": eval_results.get("avg_accuracy", 0), "mrr": eval_results.get("mrr", 0)}, 
    artifact_paths={"evaluation_report": "evaluation_report.json"}
    )

if __name__ == "__main__":
    GITHUB_URL = "https://github.com/frappe/erpnext/tree/develop/erpnext/accounts/doctype/sales_invoice"
    asyncio.run(run_modernization_pipeline(GITHUB_URL))