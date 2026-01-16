import networkx as nx
import os

def export_folder_to_mermaid(gexf_path, folder_name="sales_invoice", output_file="sales_invoice_flow.md"):
    if not os.path.exists(gexf_path):
        print(f"❌ Error: {gexf_path} not found.")
        return

    # Load the graph
    G = nx.read_gexf(gexf_path)
    
    # Normalize our target string for a flexible match
    target = folder_name.replace("\\", "/").lower()

    # 1. Identify nodes where the NODE ID itself contains the folder name
    target_nodes = [
        node for node in G.nodes()
        if target in node.replace("\\", "/").lower()
    ]

    if not target_nodes:
        print(f"❌ Still no nodes found for '{folder_name}'.")
        return

    # 2. Create the subgraph
    subgraph = G.subgraph(target_nodes)

    # 3. Build Mermaid String
    mermaid_lines = ["graph TD"]
    for u, v in subgraph.edges():
        # Clean IDs for Mermaid (no backslashes or colons)
        u_id = u.replace("\\", "_").replace("/", "_").replace(":", "_").replace(".", "_")
        v_id = v.replace("\\", "_").replace("/", "_").replace(":", "_").replace(".", "_")
        
        # Label: show only the part after the last colon (the function name)
        u_label = u.split(":")[-1] if ":" in u else u.split("\\")[-1]
        v_label = v.split(":")[-1] if ":" in v else v.split("\\")[-1]
        
        mermaid_lines.append(f"    {u_id}[\"{u_label}\"] --> {v_id}[\"{v_label}\"]")

    mermaid_code = "\n".join(mermaid_lines)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(f"### Flow for `{folder_name}`\n\n```mermaid\n{mermaid_code}\n```")

    print(f"✅ Success! Found {len(target_nodes)} nodes and saved to {output_file}")

if __name__ == "__main__":
    # Just use the folder name 'sales_invoice' since it's part of the path
    export_folder_to_mermaid("sales_invoice_graph.gexf", folder_name="sales_invoice")
