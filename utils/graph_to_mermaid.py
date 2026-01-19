import networkx as nx
import os

def export_folder_to_mermaid(gexf_path, folder_name="SalesInvoice", output_file="sales_invoice_flow.md"):
    if not os.path.exists(gexf_path):
        print(f"❌ Error: {gexf_path} not found.")
        return

    # Load the graph
    G = nx.read_gexf(gexf_path)
    
    # Convert 'SalesInvoice' to 'sales_invoice' for path matching
    folder_target = folder_name.lower()
    snake_target = "".join(['_' + i.lower() if i.isupper() else i for i in folder_name]).lstrip('_').lower()

    # 1. Identify nodes (Files or Functions) that belong to this entity
    target_nodes = []
    for node in G.nodes():
        node_clean = node.replace("\\", "/").lower()
        # Match if either "SalesInvoice" or "sales_invoice" is in the path/ID
        if folder_target in node_clean or snake_target in node_clean:
            target_nodes.append(node)

    if not target_nodes:
        print(f"❌ No nodes found matching '{folder_name}' or '{snake_target}' in the graph.")
        return

    # 2. Create the subgraph including these nodes
    subgraph = G.subgraph(target_nodes)

    # 3. Build Mermaid String
    mermaid_lines = ["graph TD"]
    
    # Track edges to avoid duplicates in MultiDiGraph
    seen_edges = set()

    for u, v in subgraph.edges():
        edge_key = (u, v)
        if edge_key in seen_edges:
            continue
        seen_edges.add(edge_key)

        # Clean IDs for Mermaid (Must be alphanumeric/underscores)
        u_id = u.replace("\\", "_").replace("/", "_").replace(":", "_").replace(".", "_")
        v_id = v.replace("\\", "_").replace("/", "_").replace(":", "_").replace(".", "_")
        
        # Labeling Logic:
        # If ID contains ':', it's a function (show function name).
        # If no ':', it's a file (show filename).
        u_label = u.split(":")[-1] if ":" in u else u.split("/")[-1]
        v_label = v.split(":")[-1] if ":" in v else v.split("/")[-1]
        
        mermaid_lines.append(f"    {u_id}[\"{u_label}\"] --> {v_id}[\"{v_label}\"]")

    mermaid_code = "\n".join(mermaid_lines)

    # Save to Markdown
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(f"### Logic Flow for `{folder_name}`\n\n")
        f.write(f"This diagram shows the relationships between files and functions discovered in the repository.\n\n")
        f.write(f"```mermaid\n{mermaid_code}\n```")

    print(f"✅ Success! Generated Mermaid flow with {len(target_nodes)} nodes at {output_file}")

if __name__ == "__main__":
    
    export_folder_to_mermaid("SalesInvoice_graph.gexf", folder_name="SalesInvoice")