# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a RAG (Retrieval-Augmented Generation) system that combines Solr for document retrieval with LLM providers (Ollama or OpenAI) for conversational AI. The system downloads, filters, indexes documents, and provides a Streamlit-based chat interface where users can query information with automatic context retrieval.

## Architecture

### Core Components

**Data Pipeline** (`__main__.py`):
- Entry point orchestrating the entire workflow: download → filter → upload → UI
- Configurable via command-line flags for running individual steps or the complete pipeline
- Uses `subfolder_processors` dictionary to map data source folders to their specialized filter implementations

**LLM Abstraction** (`LLM/client.py`):
- Base class `LLM_Client` provides provider-agnostic interface
- Manages conversation history and assistant contexts (loaded from `LLM/contexts/*.txt`)
- Handles automatic query detection: questions ending with `?` or messages >8 words trigger Solr search
- `insertion_format` template injects retrieved context into prompts
- Implementations: `OllamaClient` (local models) and `OpenAI_Client` (API-based)

**Document Retrieval** (`retrieval/solr_handler.py`):
- `SolrHandler` performs language-aware search with stopword filtering
- Uses edismax query parser with field boosting: title^2, language-specific text fields
- Implements custom scoring: combines Solr scores with word frequency matching
- Falls back to English search if no results found in detected language
- Currently returns single best document (see line 119 comment about multi-doc support)

**Data Processing** (`retrieval/filters.py`):
- `DataFilter` base class with three specialized implementations:
  - `MicrosoftDocFilter`: Extracts content after configurable start phrase (e.g., "Gilt für:")
  - `WikiFilter`: Parses MediaWiki markup, handles templates/infoboxes, removes navigation sections
  - `DbFilter`: Handles PDFs (splits into 10-page chunks) and HTML, manages encoding issues (windows-1250 → utf-8)

**UI Layer** (`UI/ui.py`):
- Streamlit chat interface with assistant selection dropdown
- Displays data sources in expandable sections below AI responses
- `/clear` command resets conversation context
- LLM provider selection: comment/uncomment lines 24-25 to switch between Ollama and OpenAI

### Data Flow

1. **Download**: `Downloader` reads `data/*/urls.txt` files, downloads content, generates `urls.json` mapping
2. **Filter**: Specialized filters process raw downloads into title + content format saved to `filtered/` directory
3. **Upload**: `SolrHandler.upload_forlder` indexes filtered documents with id, title, text, url fields
4. **Query**: User message → language detection → Solr search → context injection → LLM response

### Key Design Decisions

- **Language Support**: English, German, Hungarian with stopword files in `retrieval/volume/data/ragcore/conf/lang/`
- **Solr Schema**: Uses dynamic fields `text_{language}` for multilingual indexing
- **Query Strategy**: Automatic retrieval triggered by message characteristics (length/punctuation) rather than explicit commands (unless `use_explicit_query=True`)
- **Context Format**: Retrieved documents injected as system messages between user messages

## Development Commands

### Initial Setup (First Time)

```bash
# 1. Start Solr
docker pull solr
docker create --name solr_server -v ./retrieval/volume:/var/solr -p 8983:8983 -e SOLR_SECURITY_MANAGER_ENABLED=false solr
docker start solr_server

# 2. Reload Solr core
# Visit: http://localhost:8983/solr/admin/cores?action=RELOAD&core=ragcore

# 3. Start Ollama (if using local models)
docker pull ollama/ollama
docker create --name ollama_docker --restart unless-stopped -v ./LLM/ollama:/root/.ollama -p 11434:11434 -e OLLAMA_KEEP_ALIVE=24h -e OLLAMA_HOST=0.0.0.0 ollama/ollama
docker start ollama_docker
docker exec -it ollama_docker ollama run <model_name>

# 4. Install Python dependencies (requires Python 3.9 for Streamlit)
pip install python-dotenv ollama beautifulsoup4 pypdf pysolr wikitextparser streamlit langdetect openai

# 5. Configure .env file (see Environment Configuration section)

# 6. Run complete pipeline
python __main__.py --all
```

### Regular Usage

```bash
# Start UI only (after data is indexed)
python __main__.py --ui

# Re-download and re-process data
python __main__.py --download --filter --upload

# Process data without launching UI
python __main__.py --process-data

# Individual steps
python __main__.py --download
python __main__.py --filter
python __main__.py --upload
python __main__.py --keep-data  # Preserve filtered/ directory after upload
```

### Docker Management

```bash
# Start/stop services
docker start solr_server
docker start ollama_docker

# Check Ollama running models
docker exec -it ollama_docker ollama ps

# Pull new Ollama model
docker exec -it ollama_docker ollama run <model_name>

# Access Solr admin UI
open http://localhost:8983/solr
```

## Environment Configuration

Create `.env` in project root:

```env
SOLR_SERVER=localhost:8983
CORE_NAME=ragcore
UI_PORT=8501

# Ollama (for local models)
OLLAMA_SERVER=localhost:11434
OLLAMA_MODEL=<model_name:details>

# OpenAI (for API-based models)
OPENAI_MODEL=<model_name>
OPENAI_API_KEY=<api_key>
```

## Switching LLM Providers

Edit `UI/ui.py` lines 24-25:

```python
# For Ollama (default):
client = OllamaClient(os.environ.get("OLLAMA_SERVER"), os.environ.get("OLLAMA_MODEL"), solr_handler)
#client = OpenAI_Client(os.environ.get("OPENAI_API_KEY"), os.environ.get("OPENAI_MODEL"), solr_handler)

# For OpenAI:
#client = OllamaClient(os.environ.get("OLLAMA_SERVER"), os.environ.get("OLLAMA_MODEL"), solr_handler)
client = OpenAI_Client(os.environ.get("OPENAI_API_KEY"), os.environ.get("OPENAI_MODEL"), solr_handler)
```

## Adding New Data Sources

1. Create subfolder in `data/` directory (e.g., `data/newsource/`)
2. Add `urls.txt` file with one URL per line
3. Create custom filter class inheriting from `DataFilter` in `retrieval/filters.py`
4. Register in `__main__.py` line 56-60:

```python
subfolder_processors = {
    "microsoft": MicrosoftDocFilter('Gilt für:'),
    "wiki": WikiFilter(url_for_id),
    "db": DbFilter(),
    "newsource": YourCustomFilter()  # Add here
}
```

## Adding New Assistants

1. Create text file in `LLM/contexts/<AssistantName>.txt` with system prompt
2. Assistant automatically appears in UI dropdown (loaded via `load_assistant_names()`)
3. See existing examples: Master.txt, Expert.txt, Tutor.txt

## Important File Locations

- **Assistant prompts**: `LLM/contexts/*.txt`
- **Stopword lists**: `retrieval/volume/data/ragcore/conf/lang/stopwords_{en,de,hu}.txt`
- **Solr configuration**: `retrieval/volume/data/ragcore/conf/`
- **Download cache**: `data/urls.json` (maps filenames to source URLs)
- **Filtered data**: `filtered/` (temporary, deleted unless `--keep-data` flag used)

## Known Limitations

- Currently returns only single best document per query (see `solr_handler.py:119`)
- Ollama model must be running before starting UI (no auto-start)
- PDF splitting hardcoded to 10 pages per chunk (`filters.py:15`)
- No authentication on Solr (Docker flag `SOLR_SECURITY_MANAGER_ENABLED=false`)
- Query detection heuristic may trigger false positives/negatives
