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

## Current Scope 

This project is intentionally scoped for learning and validation:

* **Target system:** ERPNext
* **Target module:** `erpnext/accounts/doctype/sales_invoice/`
* **Language:** Python only
* **Analysis type:** Static analysis (no runtime tracing yet)
* **Graph coverage:** Function calls, imports, and containment
* **Goal:** Understanding and impact analysis, not migration

---

## Example Query : 
`What happens internally when a Sales Invoice is submitted in ERPNext?`
```
{
    "event": "What happens internally when a Sales Invoice is submitted in ERPNext?",
    "executive_summary": "When a Sales Invoice is submitted in ERPNext, the system validates the data, creates accounting entries, updates stock (if applicable), and triggers post-submission processes. This ensures accurate financial reporting, inventory management, and fulfillment of inter-company transactions.",
    "execution_phases": {
        "VALIDATION": [
            {
                "function": "validate",
                "description": "Performs various data integrity checks, including auto-setting posting time, validating write-off accounts, fixed assets, item cost centers, and income accounts.",
                "condition": "Mandatory"
            },
            {
                "function": "validate_accounts",
                "description": "Validates the accounts associated with the Sales Invoice, such as ensuring the write-off account is valid.",
                "condition": "Mandatory"
            },
            {
                "function": "validate_for_repost",
                "description": "Validates the document for reposting scenarios, ensuring data consistency.",
                "condition": "Mandatory"
            },
            {
                "function": "validate_fixed_asset",
                "description": "Validates the fixed asset details if any asset is linked to the sales invoice.",
                "condition": "If Asset"
            },
            {
                "function": "validate_item_cost_centers",
                "description": "Validates the cost centers associated with each item in the Sales Invoice.",
                "condition": "Mandatory"
            },
            {
                "function": "validate_income_account",
                "description": "Validates the income account associated with the Sales Invoice.",
                "condition": "Mandatory"
            },
            {
                "function": "validate_pos_paid_amount",
                "description": "Validates the paid amount in POS invoices.",
                "condition": "If POS"
            },
            {
                "function": "validate_warehouse",
                "description": "Validates the warehouse selected in the Sales Invoice.",
                "condition": "Mandatory"
            },
            {
                "function": "validate_created_using_pos",
                "description": "Validates POS opening entry.",
                "condition": "If POS"
            }
        ],
        "ACCOUNTING_LOGIC": [
            {
                "function": "make_gl_entries",
                "description": "Generates General Ledger (GL) entries based on the Sales Invoice data. This includes creating customer GL entries and GL entries for fixed assets.",
                "condition": "Mandatory"
            },
            {
                "function": "get_gl_entries",
                "description": "Retrieves the GL entries for the Sales Invoice, including entries for customers and fixed assets.",
                "condition": "Mandatory"
            },
            {
                "function": "make_customer_gl_entry",
                "description": "Creates GL entries specifically for the customer involved in the Sales Invoice.",
                "condition": "Mandatory"
            },
            {
                "function": "get_gl_entries_for_fixed_asset",
                "description": "Creates GL entries for fixed assets.",
                "condition": "If Perpetual Inventory"
            },
            {
                "function": "make_pos_gl_entries",
                "description": "Creates GL entries for POS invoices, including entries for change amounts.",
                "condition": "If POS"
            },
            {
                "function": "get_gle_for_change_amount",
                "description": "Retrieves GL entries for change amounts in POS invoices.",
                "condition": "If POS"
            }
        ],
        "STOCK_LOGIC": [
            {
                "function": "update_stock",
                "description": "Updates the stock levels in the warehouse based on the items sold in the Sales Invoice.",
                "condition": "If update_stock is checked"
            }
        ],
        "POST_SUBMISSION_HOOKS": [
            {
                "function": "make_inter_company_purchase_invoice",
                "description": "Creates an inter-company purchase invoice if the Sales Invoice involves an inter-company transaction.",
                "condition": "If Inter-company"
            },
            {
                "function": "make_inter_company_transaction",
                "description": "Creates an inter-company transaction document.",
                "condition": "If Inter-company"
            },
            {
                "function": "update_time_sheet",
                "description": "Updates the time sheet details if the Sales Invoice is linked to a time sheet.",
                "condition": "If Time Sheet"
            },
            {
                "function": "update_billed_qty_in_scio",
                "description": "Updates the billed quantity in subcontracting inward order received item.",
                "condition": "If Subcontracting"
            }
        ]
    },
    "accounting_impact": "The submission of a Sales Invoice results in GL entries that debit the Debtors account (or a similar receivable account) and credit the Sales account (or relevant income account). If applicable, entries are also made for taxes, discounts, cost of goods sold (COGS), and inventory. For POS invoices, entries are made for the mode of payment and change amount.",    
    "stock_impact": "If 'update_stock' is enabled, the submission of a Sales Invoice decreases the quantity of items in the specified warehouse. Stock Ledger Entries are created to track these changes.",
    "critical_business_rules": [
        "Credit limit validation: The system checks if the customer's credit limit is exceeded by the invoice amount.",
        "Mandatory fields: Certain fields, such as customer, posting date, and item details, must be filled in for the Sales Invoice to be submitted.",
        "Accounting period: The posting date must fall within an open accounting period.",
        "Stock availability: If 'update_stock' is enabled, there must be sufficient stock in the warehouse to fulfill the order.",
        "Inter-company transaction rules: If the Sales Invoice involves an inter-company transaction, specific rules and validations apply to ensure proper accounting between the companies."     
    ]
}

```

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
<p align="center">
  <img src="assets/sales_invoice_er.png" alt="System Dependency Map">
  <br>
  <i>Figure 1: Automated Graph-to-Mermaid export showing SalesInvoice dependencies.</i>
</p>
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
