import os
import time
import json
import asyncio
import numpy as np
import google.generativeai as genai
from rank_bm25 import BM25Okapi
from engine.embedder import BGEEmbedder 
from data.storage import VectorStore 
from dotenv import load_dotenv

load_dotenv()

TEMPLATES = {
    "process_flow": """
        ## Domain Context: {entity_name} (Selling Bounded Context)
        Act as a Senior System Analyst. Explain the step-by-step internal execution flow.
        
        {context_data}
        
        INSTRUCTIONS:
        1. Use the 'Call Flow' section to trace logic.
        2. Group by VALIDATION, ACCOUNTING, and STOCK phases.
    """,
    "debugging": """
        ## Domain Context: {entity_name} (Technical Logic Trace)
        Act as a Lead Developer. Help me understand the specific logic for: {user_query}.
        
        {context_data}
    """
}

class ModernizationChat:
    def __init__(self, db_path=None, graph_path=None):
        self.api_key = os.getenv("GENAI_API_KEY")
        if not self.api_key:
            raise ValueError("❌ GENAI_API_KEY not found.")

        genai.configure(api_key=self.api_key)
        self.llm = genai.GenerativeModel('gemini-2.0-flash') 
        self.embedder = BGEEmbedder()
        self.store = VectorStore(db_path=db_path) if db_path else VectorStore()
        
        self._table = None 
        self.entity_name = "Sales Invoice"
        
        # Load graph for expansion
        self.cached_graph = self.store.load_graph(self.entity_name)

    @property
    def table(self):
        if self._table is None:
            self._table = self.store.get_table()
        return self._table

    async def get_hybrid_context(self, query: str, limit: int = 8):
        """
        Implements Hybrid Retrieval (Vector + BM25) with RRF fusion.
        """
        if self.table is None:
            return "Error: Vector table not found.", 0, 0

        t_start = time.perf_counter()
        
        # 1. Dense Search (Vector)
        query_vec = (await asyncio.to_thread(self.embedder.embed_batch, [query]))[0]
        dense_results = self.table.search(query_vec).limit(limit * 2).to_list()

        # 2. Sparse Search (BM25)
        all_chunks = self.table.to_pandas()
        tokenized_corpus = [str(c).lower().split() for c in all_chunks['content']]
        bm25 = BM25Okapi(tokenized_corpus)
        sparse_scores = bm25.get_scores(query.lower().split())
        
        # 3. Reciprocal Rank Fusion (RRF)
        fused_indices = self._rrf_fusion(dense_results, all_chunks, sparse_scores, limit)
        top_chunks = all_chunks.iloc[fused_indices]

        # 4. Context Assembly 
        formatted_context = self._format_3_part_context(top_chunks, query)
        
        total_retrieval_ms = (time.perf_counter() - t_start) * 1000
        return formatted_context, total_retrieval_ms

    def _rrf_fusion(self, dense, all_df, sparse_scores, limit, k=60):
        """Reciprocal Rank Fusion logic from Case Study."""
        scores = {}
        # Dense Ranks
        for rank, res in enumerate(dense):
            idx = all_df[all_df['id'] == res['id']].index[0]
            scores[idx] = scores.get(idx, 0) + 1.0 / (k + rank + 1)
        # Sparse Ranks
        sparse_rank_indices = np.argsort(sparse_scores)[::-1][:limit*2]
        for rank, idx in enumerate(sparse_rank_indices):
            scores[idx] = scores.get(idx, 0) + 1.0 / (k + rank + 1)
        
        return sorted(scores.keys(), key=lambda x: scores[x], reverse=True)[:limit]

    def _format_3_part_context(self, chunks_df, query):
        """Formats context into two sections: Relevant Code & Call Flow Diagram."""
        context_parts = ["## Relevant Code\n"]
        
        for _, row in chunks_df.iterrows():
            chunk_header = f"### {row['symbol_name']} ({row['symbol_type']})\n"
            chunk_meta = f"**File**: `{row['file_path']}:{row['start_line']}`\n"
            chunk_meta += f"**Hook**: {row.get('hook_type') or 'N/A'}\n"
            
            chunk_code = f"```python\n{row['content']}\n```\n"
            context_parts.append(chunk_header + chunk_meta + chunk_code)

        # Call Flow Diagram (Placeholder logic)
        context_parts.append("\n## Call Flow\n```\n" + self._generate_mermaid_flow(chunks_df) + "\n```")
        return "\n".join(context_parts)

    def _generate_mermaid_flow(self, chunks_df):
        """Basic representation of relationships."""
        flow = []
        for name in chunks_df['symbol_name'].unique():
            flow.append(f"  └── {name}()")
        return "\n".join(flow)

    async def generate_domain_model(self, folder_path, query=None):
        active_query = query if query else f"Overview of {self.entity_name}"
        
        # Retrieval
        context_text, r_lat = await self.get_hybrid_context(active_query)

        # Generation
        selected_template = TEMPLATES["process_flow"] if "flow" in active_query.lower() else TEMPLATES["debugging"]
        final_prompt = selected_template.format(
            entity_name=self.entity_name,
            user_query=active_query,
            context_data=context_text
        )

        start_gen = time.perf_counter()
        response = await self.llm.generate_content_async(
            final_prompt,
            generation_config={"response_mime_type": "application/json", "temperature": 0.1}
        )
        g_lat = (time.perf_counter() - start_gen) * 1000

        return response.text, r_lat, g_lat
    
if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()
    
    async def main():
        chat_agent = ModernizationChat()
        response, retrieval_time, gen_time = await chat_agent.generate_domain_model(
            folder_path="path/to/local/repo",
            query="Explain the validation and accounting process flow"
        )
        print("=== Generated Response ===")
        print(response)
        print(f"\nRetrieval Time: {retrieval_time:.2f} ms")
        print(f"Generation Time: {gen_time:.2f} ms")
    
    asyncio.run(main())