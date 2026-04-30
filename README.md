# Smart Document Processing System

A web application for processing business documents (invoices and purchase orders), extracting structured data, validating it, and reviewing results through a simple interface.

---

## 📌 Overview

This system allows users to upload documents (PDF, CSV, TXT), automatically extracts key information, validates it, and provides a review interface for manual corrections.

The goal is to handle real-world imperfect data and detect inconsistencies.

---

## ✨ Features

### 📥 Document Ingestion
- Upload support for:
  - PDF
  - CSV
  - TXT
- Automatic file type detection

---

### 🧠 Data Extraction
Extracts:
- Supplier name
- Document number
- Issue date / Due date
- Currency
- Subtotal, tax, total
- Line items (quantity, price, total)

---

### 🔍 Validation Engine

Automatically validates:

- ✅ Required fields (supplier, document number, issue date)
- ✅ Total calculation (subtotal + tax = total)
- ✅ Line item calculations (quantity × unit_price = total)
- ✅ Duplicate document numbers

---

### ⚠️ Issue Detection

- Errors → block validation
- Warnings → highlight inconsistencies

---

### 🧾 Review Interface

- View extracted data
- See validation issues (highlighted)
- Edit document fields
- Re-run validation
- Mark as validated or reject document

---

### 📊 Dashboard

- List all documents
- View statuses:
  - Uploaded
  - Needs Review
  - Validated
  - Rejected
- Quick overview of documents

---

## 🏗️ Tech Stack

- **Backend:** Django
- **Database:** SQLite (development)
- **Frontend:** Django Templates + Bootstrap
- **Parsing:**
  - pdfplumber (PDF)
  - built-in CSV/TXT parsing
- **Validation:** Custom validation engine

## 🧠 Approach

The system is designed as a pipeline:

1. Document Upload
2. Parsing Layer
3. Validation Engine
4. Review Interface

### Parsing Strategy
- Used regex-based extraction for PDF/TXT
- Structured parsing for CSV
- Designed to handle imperfect input data

### Validation Strategy
- Separate validation layer
- Clear separation between extraction and validation
- Uses tolerance for financial calculations

### Design Decisions
- Django templates for simplicity
- Service layer for parsing and validation
- Modular and extensible architecture

- ## 🤖 AI Usage

AI tools (ChatGPT and Claude) were used for:
- Code scaffolding
- Regex improvements
- Debugging assistance

All code was reviewed, tested, and adapted manually.

## 🚀 Future Improvements

- OCR support for image documents
- Advanced PDF layout parsing
- API layer (Django REST Framework)
- Docker containerization
- Automated tests
- Multi-user support
