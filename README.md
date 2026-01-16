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

## Example Query : Explain the core domain logic and state transitions of {self.entity_name}
```
{
    "SalesInvoice": {
        "entry_point": "erpnext/accounts/doctype/sales_invoice/sales_invoice.py:submit()",
        "entry_point_description": "Framework method call to submit the Sales Invoice, triggering business logic, accounting updates, and stock movements.",
        "workflow": {
            "VALIDATION": [
                {
                    "method": "Advance Allocation Strategy",
                    "description": "Controls whether advances are automatically allocated or require manual specification and validation.",
                    "context": "erpnext/accounts/doctype/sales_invoice/test_sales_invoice.py:test_sales_invoice_with_advance"
                },
                {
                    "method": "Deferred Revenue Account Check",
                    "description": "Ensures that a deferred revenue account is specified if deferred revenue booking is enabled for an item.",
                    "context": "erpnext/accounts/doctype/sales_invoice/test_sales_invoice.py:test_deferred_revenue_missing_account"
                },
                {
                    "method": "Item Tax Template Range Application",
                    "description": "Dynamically selects and applies the correct item tax template based on the net rate of the item, adjusting for discounts.", 
                    "context": "erpnext/accounts/doctype/sales_invoice/test_sales_invoice.py:test_item_tax_net_range"
                },
                {
                    "method": "Inter-company Address Link Verification",
                    "description": "Validates that company and customer addresses are correctly linked to their respective entities for inter-company transactions.",
                    "context": "erpnext/accounts/doctype/sales_invoice/test_sales_invoice.py:test_validate_inter_company_transaction_address_links"
                },
                {
                    "method": "Serial Number Consistency Check",
                    "description": "Verifies that serial numbers assigned to items on the Sales Invoice match those from the originating Delivery Note.",       
                    "context": "erpnext/accounts/doctype/sales_invoice/test_sales_invoice.py:test_serial_numbers_against_delivery_note"
                }
            ],
            "ACCOUNTING": [
                {
                    "method": "General Ledger (GL) Entry Generation",
                    "description": "Creates debits and credits for accounts such as Debtors, Sales, Income, Discount, and Cost of Goods Sold upon submission.", 
                    "context": "erpnext/accounts/doctype/sales_invoice/test_sales_invoice.py:test_sales_invoice_gl_entry_with_perpetual_inventory_non_stock_item"
                },
                {
                    "method": "Advance Allocation and Outstanding Amount Update",
                    "description": "Allocates specified advances to reduce the invoice's outstanding amount and reflects this in GL entries.",
                    "context": "erpnext/accounts/doctype/sales_invoice/test_sales_invoice.py:test_sales_invoice_with_advance"
                },
                {
                    "method": "Deferred Revenue Recognition",
                    "description": "Generates GL entries to progressively recognize deferred revenue based on service dates and accounting periods.",
                    "context": "erpnext/accounts/doctype/sales_invoice/test_sales_invoice.py:test_deferred_revenue"
                },
                {
                    "method": "Discount Accounting Posting",
                    "description": "Posts item-level and additional discounts to a dedicated discount account when discount accounting is enabled.",
                    "context": "erpnext/accounts/doctype/sales_invoice/test_sales_invoice.py:test_sales_invoice_with_discount_accounting_enabled"
                },
                {
                    "method": "Tax Account Posting",
                    "description": "Records calculated taxes (e.g., VAT, TDS) against the relevant tax account heads in the GL.",
                    "context": "erpnext/accounts/doctype/sales_invoice/test_sales_invoice.py:test_additional_discount_for_sales_invoice_with_discount_accounting_enabled"
                },
                {
                    "method": "Stock Transfer Rounding Adjustment",
                    "description": "Creates GL adjustment entries to account for precision differences during stock unit of measure conversions in internal transfers.",
                    "context": "erpnext/accounts/doctype/sales_invoice/test_sales_invoice.py:test_internal_transfer_gl_precision_issues"
                }
            ],
            "STOCK": [
                {
                    "method": "Stock Quantity Reduction",
                    "description": "Updates warehouse stock levels by reducing the quantity of items sold or, for returns, increasing it.",
                    "context": "erpnext/accounts/doctype/sales_invoice/test_sales_invoice.py:test_return_sales_invoice"
                },
                {
                    "method": "Serialized Item Status Management",
                    "description": "Marks serialized items as sold (updating their warehouse status to null) upon invoice submission and reinstates them upon cancellation.",
                    "context": "erpnext/accounts/doctype/sales_invoice/test_sales_invoice.py:test_serialized"
                },
                {
                    "method": "Stock Ledger Entry (SLE) Creation",
                    "description": "Records detailed stock movements, valuations, and cost of goods sold in the Stock Ledger.",
                    "context": "erpnext/accounts/doctype/sales_invoice/test_sales_invoice.py:test_return_sales_invoice"
                },
                {
                    "method": "Stock Unit of Measure Conversion",
                    "description": "Performs conversions between non-stock and stock units of measure, especially relevant for internal transfers.",
                    "context": "erpnext/accounts/doctype/sales_invoice/test_sales_invoice.py:test_internal_transfer_gl_precision_issues"
                }
            ],
            "HOOKS": [
                {
                    "method": "Inter-company Transaction Creation",
                    "description": "Automatically triggers the creation of a corresponding Purchase Invoice or Purchase Order when a Sales Invoice is raised for an internal customer.",
                    "context": "erpnext/accounts/doctype/sales_invoice/test_sales_invoice.py:test_inter_company_transaction"
                },
                {
                    "method": "Implicit Accounting Ledger Reposting",
                    "description": "Modifications and saves to a submitted Sales Invoice automatically trigger a reposting of associated accounting ledgers to reflect changes.",
                    "context": "erpnext/accounts/doctype/sales_invoice/test_sales_invoice.py:test_additional_discount_for_sales_invoice_with_discount_accounting_enabled"
                }
            ]
        },
        "contextual_overlays": [
            {
                "type": "Setting",
                "name": "unlink_payment_on_cancellation_of_invoice",
                "description": "A system setting that dictates whether payments linked to an invoice are automatically unlinked when the invoice is cancelled.",
                "context": "erpnext/accounts/doctype/sales_invoice/test_sales_invoice.py:test_sales_invoice_with_advance"
            },
            {
                "type": "Setting",
                "name": "book_deferred_entries_based_on",
                "description": "A system setting determining the basis ('days' or 'months') for prorating deferred revenue recognition.",
                "context": "erpnext/accounts/doctype/sales_invoice/test_sales_invoice.py:test_deferred_revenue"
            },
            {
                "type": "Setting",
                "name": "book_deferred_entries_via_journal_entry",
                "description": "A system setting indicating whether deferred revenue entries are processed via Journal Entries or direct GL updates (0 implies direct GL in these tests).",
                "context": "erpnext/accounts/doctype/sales_invoice/test_sales_invoice.py:test_deferred_revenue"
            },
            {
                "type": "Setting",
                "name": "enable_discount_accounting",
                "description": "A system setting that, when enabled, allows discounts to be separately accounted for in the General Ledger.",
                "context": "erpnext/accounts/doctype/sales_invoice/test_sales_invoice.py:test_sales_invoice_with_discount_accounting_enabled"
            },
            {
                "type": "Quirk",
                "name": "GL Precision Handling for Internal Transfers",
                "description": "The system specifically handles potential rounding errors arising from unit of measure conversions in internal transfers by creating adjustment GL entries.",
                "context": "erpnext/accounts/doctype/sales_invoice/test_sales_invoice.py:test_internal_transfer_gl_precision_issues"
            }
        ]
    }
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
