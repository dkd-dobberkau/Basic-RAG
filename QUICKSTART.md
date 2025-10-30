# Quick Start Guide

Your RAG system is now set up and ready to use!

## What's Been Configured

✅ **Solr** - Running on `localhost:8983`

✅ **Ollama** - Running on `localhost:11434` with `llama3.2:3b` model

✅ **Python dependencies** - All packages installed

✅ **.env file** - Environment variables configured

✅ **Data directories** - Created with sample structure


## Current Status

```bash
# Check running containers
docker ps

# You should see:
# - solr_server (port 8983)
# - ollama_docker (port 11434)
```

## Next Steps

### 1. Add Your Data Sources

Add URLs to the files in the `data/` directory:
- `data/wiki/urls.txt` - Wikipedia articles
- `data/microsoft/urls.txt` - Microsoft documentation
- `data/db/urls.txt` - Database documentation (PDFs, HTML)

Example for `data/wiki/urls.txt`:
```
https://en.wikipedia.org/wiki/Python_(programming_language)
https://en.wikipedia.org/wiki/Machine_learning
https://en.wikipedia.org/wiki/Natural_language_processing
```

### 2. Download, Process, and Index Data

Run the complete pipeline:
```bash
python __main__.py --all
```

Or run individual steps:
```bash
# Download data
python __main__.py --download

# Filter and clean data
python __main__.py --filter

# Upload to Solr
python __main__.py --upload

# Start UI
python __main__.py --ui
```

### 3. Launch the Chat Interface

The UI will automatically start after running `--all`, or manually:
```bash
python __main__.py --ui
```

Access at: **http://localhost:8501**

## Managing Docker Containers

### Stop Services
```bash
docker stop solr_server ollama_docker
```

### Start Services
```bash
docker start solr_server ollama_docker
```

### View Logs
```bash
# Solr logs
docker logs solr_server

# Ollama logs
docker logs ollama_docker
```

## Access Points

- **Streamlit UI**: http://localhost:8501
- **Solr Admin**: http://localhost:8983/solr
- **Ollama API**: http://localhost:11434

## Switching to OpenAI

1. Edit `.env` and add your OpenAI API key:
   ```env
   OPENAI_MODEL=gpt-4
   OPENAI_API_KEY=your_api_key_here
   ```

2. Edit `UI/ui.py` lines 24-25:
   ```python
   # Comment out Ollama:
   #client = OllamaClient(os.environ.get("OLLAMA_SERVER"), os.environ.get("OLLAMA_MODEL"), solr_handler)

   # Uncomment OpenAI:
   client = OpenAI_Client(os.environ.get("OPENAI_API_KEY"), os.environ.get("OPENAI_MODEL"), solr_handler)
   ```

## Troubleshooting

### If Solr core fails to load:

The schema has been fixed to use StandardTokenizerFactory instead of ICUTokenizerFactory, and problematic update processor chains have been commented out. If you still have issues:

```bash
# Check Solr logs
docker logs solr_server

# Restart Solr
docker restart solr_server

# Verify core is loaded
curl "http://localhost:8983/solr/admin/cores?action=STATUS&core=ragcore"

# Test query
curl "http://localhost:8983/solr/ragcore/select?q=*:*"
```

### If Ollama model isn't running:
```bash
# Check running models
docker exec -it ollama_docker ollama ps

# Run the model
docker exec -it ollama_docker ollama run llama3.2:3b
```

### If Python dependencies fail:
```bash
# Reinstall with specific Python version
python3.13 -m pip install python-dotenv ollama beautifulsoup4 pypdf pysolr wikitextparser streamlit langdetect openai
```

## Chat Commands

- `/clear` - Reset conversation context
- Type questions ending with `?` or long messages (>8 words) to trigger RAG retrieval

## Available Assistants

Select from the dropdown in the UI:
- **Master** - Devil's advocate for team decisions
- **Expert** - (Check `LLM/contexts/Expert.txt` for details)
- **Tutor** - (Check `LLM/contexts/Tutor.txt` for details)

Add more assistants by creating `.txt` files in `LLM/contexts/`

## Need Help?

- See `CLAUDE.md` for detailed architecture and development guide
- See `Questions.md` for RAG implementation details
- See `README.md` for original setup instructions
