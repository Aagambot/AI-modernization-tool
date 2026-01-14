
## Project Documentation: Legacy ERP Modernization Pipeline

### Executive Summary

This project delivers an automated pipeline for extracting **Domain-Driven Design (DDD)** patterns from legacy ERP source code. By combining **Static Analysis** with **Semantic Retrieval**, we transform unstructured codebases into structured, navigable knowledge models. This enables architects to map complex business logic and dependencies with high precision.

---
### Domain Schema Visualization
![Sales Invoice ER Diagram](assets/sales_invoice_er.png)
*Figure 1: Extracted Entity Relationship Model for the Sales Invoice Aggregate.*
### Technical Architecture

* **Intelligence Layer:** LLM-driven synthesis of extracted business logic and entity relationships.
* **Vector Engine:** **LanceDB** for high-density storage and sub-second semantic search of code chunks.
* **Graph Engine:** **NetworkX** for initial call-graph extraction, with a roadmap for **Neo4j** integration for advanced multi-hop relationship queries.
* **Data Pipeline:** Standardized ingestion using **Nomic-Embed-Text** to maintain method-level context.
* **Observability:** **MLflow** for tracking retrieval accuracy, latency, and model versioning.

---

### Domain Entity Model: Sales Invoice

The pipeline successfully extracted the core schema and relationships for the `SalesInvoice` aggregate.

#### Schema Visualization

#### Key Extracted Modules

* **Validation:** Automated checks for credit limits, warehouse availability, and tax templates.
* **Financials:** Logic governing General Ledger (GL) entries and receivable balance updates.
* **Stock:** Integration points for Stock Ledger Entries (SLE) and valuation recalculations.

---

### Process & Validation 

To ensure the pipeline is enterprise-ready, we implemented a **Retrieval Verification Suite** to measure the accuracy of our context engine.

* **Metrics:**  across golden queries through file `golden_dataset.json`(e.g., "How is credit limit enforced?").
✅ Hit Rate @ 5: 100.00%
🏆 Mean Reciprocal Rank (MRR): 0.750
* **Verification:** Automatic normalization of absolute Windows paths to ensure cross-platform retrieval consistency.
* **Graph Utility:** Confirmed that the call-graph improves "Logic Findability" by identifying downstream effects of function calls (e.g., from `on_submit` to `make_gl_entries`).

---

### Implementation Note: Graph Strategy

While current visualization is handled via **NetworkX** and **Mermaid.js** for documentation clarity, the architecture is designed to shift to **Neo4j** as the repository scale increases. This will support complex queries like "Show all modules affected by a change in the Tax Calculation logic."

---