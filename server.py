import uvicorn
import os
from fastapi import FastAPI
from pydantic import BaseModel
from chat import ModernizationChat
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allows the Webview to connect
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- CONFIGURATION ---
# Point these to the folders/files you created during the initial Sales Invoice scan
DB_PATH = "./lancedb_erpnext"  # Your existing LanceDB folder
GRAPH_PATH = "./erpnext_graph.gpickle" # Your existing NetworkX graph

# Initialize the engine once with your existing data
# We assume ModernizationChat is updated to accept these paths in __init__
chat_engine = ModernizationChat()

class QueryRequest(BaseModel):
    query: str
    limit: int = 8

@app.get("/health")
async def health_check():
    return {"status": "ready", "demo_target": "sales_invoice"}

@app.post("/ask")
async def ask_logic(request: QueryRequest):
    """
    Handles queries from the VS Code Sidebar.
    No folder_path is needed because the database is already loaded.
    """
    try:
        # Generate the domain model using the pre-indexed Sales Invoice data
        model_json, r_lat, g_lat = await chat_engine.generate_domain_model(
            folder_path=None, 
            query=request.query
        )
        
        return {
            "answer": model_json,
            "metrics": {
                "retrieval_ms": r_lat, 
                "generation_ms": g_lat
            }
        }
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)