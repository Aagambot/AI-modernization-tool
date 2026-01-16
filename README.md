## Project Documentation: Legacy ERP Modernization Pipeline

---

## Overview

### Purpose of the Project

This project investigates how **code intelligence techniques** can improve the safety and confidence of legacy ERP modernization.
Rather than migrating or rewriting code, the goal is to **make existing business-critical logic understandable, traceable, and verifiable** before any changes are attempted.

The focus is on **ERPNext**, specifically the **Sales Invoice** module, which contains dense accounting, stock, and validation logic that is difficult to reason about through documentation alone.

---

## Problem Statement & Approach

### Problem Statement

Legacy ERP systems often contain:

* Business logic spread across many files and hooks
* Implicit dependencies that are hard to trace
* High risk of regression when making changes

Developers struggle to answer basic questions such as:

* *Where is a rule enforced?*
* *What functions are affected if this changes?*
* *Which workflows are triggered on submit or cancel?*

### Approach Taken

This project builds a **local-first, graph-augmented RAG pipeline** that:

1. Parses the ERPNext codebase using ASTs
2. Extracts function-level relationships into a graph
3. Embeds code chunks for semantic retrieval
4. Verifies retrieval quality using measurable metrics

The result is a **searchable and inspectable knowledge layer** over the existing codebase.

---

## Current Scope (Explicit)

This project is intentionally scoped for learning and validation:

* **Target system:** ERPNext
* **Target module:** `erpnext/accounts/doctype/sales_invoice/`
* **Language:** Python only
* **Analysis type:** Static analysis (no runtime tracing yet)
* **Graph coverage:** Function calls, imports, and containment
* **Goal:** Understanding and impact analysis, not migration

---

## Technical Architecture

### High-Level Pipeline

1. **Repository Scanning**
   The ERPNext repository is cloned locally and scanned from the filesystem to avoid API limits and ensure reproducibility.

2. **AST-Based Parsing**
   Code is parsed using **Tree-sitter** to identify functions, classes, and structural boundaries.

3. **Chunking & Embedding**

   * Code is chunked at logical boundaries with token-aware sizing
   * Chunks are embedded using **nomic-embed-text**
   * Embeddings are stored in **LanceDB** with file and line metadata

4. **Graph Construction**

   * A directed graph is built using **NetworkX**
   * Nodes represent functions and files
   * Edges represent calls, imports, and containment relationships

5. **Hybrid Retrieval (Graph + Vector)**

   * Semantic search retrieves relevant code
   * Graph traversal adds upstream and downstream context
   * Both are combined before LLM synthesis

6. **Evaluation & Tracking**

   * Retrieval quality is measured using **Hit Rate @ 5** and **MRR**
   * All runs are versioned and logged using **MLflow**

---

## Project Structure

```
AI-MODERNIZATION-TOOL/
├── core/                    # Repository scanning and graph logic
│   ├── scanner.py
│   ├── parser.py
│   └── graph_builder.py
│
├── engine/                  # Chunking and embedding logic
│   ├── chunker.py
│   └── embedder.py
│
├── data/                    # Vector storage
│   └── storage.py
│
├── utils/                   # Logging, search, and visualization
│   ├── logger.py
│   ├── search.py
│   └── graph_to_mermaid.py
│
├── tests/                   # Retrieval evaluation
│   └── verify_retrieval.py
│
├── main.py                  # End-to-end pipeline orchestration
├── chat.py                  # Retrieval + LLM interface
├── golden_dataset.json      # Benchmark queries
└── code_index_db/           # LanceDB vector database
```

---

## Extracted Understanding: Sales Invoice (Experimental)

The pipeline was used to reconstruct a **candidate execution workflow** for the Sales Invoice module based purely on static analysis.

### Observed Execution Phases (Hypotheses)

* **Validation:** Deferred revenue checks, tax template validation, inter-company address validation
* **Accounting:** GL entry creation, perpetual inventory accounting, advance allocation
* **Stock:** Stock updates, serial/batch handling, reversals on cancellation
* **Hooks:** Post-submit and post-cancel side effects driven by system settings

These phases are **derived from code structure and call relationships**, not manually curated documentation.

---

## Verification & Metrics

To ensure the system is producing useful results, a small verification suite is used.

### Retrieval Metrics (Golden Dataset)

* **Hit Rate @ 5:** 100%
* **Mean Reciprocal Rank (MRR):** 0.75

These metrics validate that:

* Relevant files are consistently retrieved
* Core business logic appears early in search results

### Supporting Checks

* Path normalization ensures graph and vector indexes stay aligned
* Graph traversal surfaces dependencies missed by vector search alone

---

## Key Learnings So Far

* Vector search alone is insufficient for understanding legacy code
* Call graphs significantly improve context and correctness
* Measuring retrieval quality is essential to avoid false confidence
* Scoping narrowly (one module) produces better insights than broad indexing

---

## Conclusion

This project demonstrates that **graph-augmented retrieval** can make complex ERP codebases more understandable and measurable.
By focusing on **structural understanding before change**, it provides a practical foundation for safer, incremental legacy modernization.

Future work can build on this foundation to explore runtime analysis, broader domain coverage, and modernization workflows.

---
