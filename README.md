# Tender & Bid Analysis System (RAG-Powered)

An end-to-end Retrieval-Augmented Generation (RAG) and document analysis system for processing tenders, validating Bill of Quantities (BOQ), analyzing risks, and comparing bidder submissions.

## Features

- **Document Extraction & OCR**: Extracts structured content from tender and bidder documents (PDF and scanned documents).
- **BOQ Extraction & Validation**: Parses Bill of Quantities Excel files, validates item totals, rates, and summaries.
- **RAG Pipeline**: Uses ChromaDB and Sentence Transformers with local LLMs (via Ollama) for question answering across tender documentation.
- **Risk Analysis**: Detects key risks, critical clauses, and deviations in bidder proposals.
- **Bidder Comparison**: Side-by-side comparison of bidders against tender requirements and automated recommendation generation.
- **Interactive Web UI**: Streamlit dashboard for uploading documents, running analyses, exploring results, and chatting with the RAG assistant.

## Tech Stack

- **Python 3.10+**
- **Streamlit**: Web application dashboard
- **ChromaDB**: Vector database for document embeddings
- **Sentence-Transformers**: Text embeddings
- **Ollama**: Local LLM serving
- **PyMuPDF & Tesseract**: PDF processing and OCR
- **Pandas & OpenPyXL**: Tabular data and BOQ processing

## Getting Started

### 1. Installation

Clone the repository and install the dependencies:

```bash
git clone https://github.com/Priya-Kumaresan/PROJ-TENDER-RAG.git
cd PROJ-TENDER-RAG
pip install -r requirements.txt
```

### 2. Run the Pipeline

You can run the ingestion and analysis pipeline directly:

```bash
python main.py
```

### 3. Launch the Streamlit App

```bash
streamlit run app.py
```
