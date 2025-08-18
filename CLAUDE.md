# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Japanese OpenAI RAG (Retrieval-Augmented Generation) demonstration project that implements a complete pipeline for downloading datasets from HuggingFace, processing them for RAG applications, and performing vector-based search using OpenAI's APIs.

## Development Commands

### Installation
```bash
pip install -r requirements.txt
```

### Running the Application
The project uses a sequential pipeline approach:

1. **Download datasets from HuggingFace:**
   ```bash
   python a30_00_dl_dataset_from_huggingface.py
   ```

2. **Process individual datasets for RAG:**
   ```bash
   python a30_011_make_rag_data_customer.py    # Customer support FAQ
   python a30_013_make_rag_data_medical.py     # Medical Q&A
   python a30_014_make_rag_data_sciq.py        # Science/Tech Q&A
   python a30_015_make_rag_data_legal.py       # Legal Q&A
   ```

3. **Create OpenAI vector store:**
   ```bash
   python a30_020_make_vsid.py
   ```

4. **Perform RAG search:**
   ```bash
   python a30_30_rag_search.py
   ```

### Streamlit Applications
Some scripts may include Streamlit UIs. Run with:
```bash
streamlit run <script_name>.py
```

## Architecture

### Core Components

- **helper_api.py**: OpenAI API wrapper and core functionality including ConfigManager, logging, and API client management
- **helper_rag.py**: RAG data preprocessing utilities and shared configuration (AppConfig class with model definitions and pricing)
- **helper_st.py**: Streamlit-specific helper functions and UI components

### Data Pipeline

1. **Dataset Sources**: Downloads from HuggingFace using the `datasets` library
2. **Processing Scripts**: Individual processors for different domain datasets (customer support, medical, science, legal)
3. **Vector Storage**: Integration with OpenAI's vector store API
4. **Search Interface**: RAG-based search implementation

### Configuration

- **config.yml**: Comprehensive application configuration including:
  - Model settings (supports GPT-4o, o1, o3, o4 series)
  - API configuration with timeout and retry settings
  - UI settings for Streamlit applications
  - Multi-language support (Japanese/English)
  - Pricing information for token cost calculation

### Data Flow

```
HuggingFace Datasets → CSV files → Processed TXT files → OpenAI Vector Store → RAG Search
```

### File Structure

- `datasets/`: Raw CSV files downloaded from HuggingFace
- `OUTPUT/`: Processed files and metadata
- `doc/`: Documentation in markdown format
- Configuration managed through `config.yml` and environment variables

## Environment Variables

- `OPENAI_API_KEY`: Required for OpenAI API access
- `OPENWEATHER_API_KEY`: Optional for weather integration demos

## Key Features

- Multi-domain dataset support (customer support, medical, scientific, legal)
- Japanese language focus with bilingual error messages
- Token usage tracking and cost calculation
- Comprehensive logging and error handling
- Streamlit UI components for interactive demonstrations
- Vector store management with OpenAI's API

## Development Notes

- The project follows a numbered naming convention (a30_*) for sequential execution
- Each processing script generates both processed data and metadata files
- Configuration is centralized in `config.yml` with extensive customization options
- Helper modules provide reusable functionality across the pipeline