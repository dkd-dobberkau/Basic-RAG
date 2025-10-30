# Setup and Debugging Log

This document tracks all the steps taken to set up the RAG system locally and the issues resolved along the way.

## Initial Setup

### 1. Docker Containers
- **Solr**: Set up at `localhost:8983` with core `ragcore`
- **Ollama**: Set up at `localhost:11434` with model `llama3.2:3b`

### 2. Environment Configuration
Created `.env` file:
```env
SOLR_SERVER=localhost:8983
CORE_NAME=ragcore
OLLAMA_SERVER=localhost:11434
OLLAMA_MODEL=llama3.2:3b
UI_PORT=8501
```

### 3. Python Dependencies
Installed all required packages from `requirements.txt`

### 4. Data Directories
Created `data/wiki`, `data/microsoft`, `data/db` directories

---

## Issues Encountered and Fixed

### Error 1: Solr ICUTokenizerFactory Missing
**Error**: `Error loading class 'solr.ICUTokenizerFactory'`

**Root Cause**: Schema used ICUTokenizerFactory which requires ICU Analysis plugin not in Docker image

**Fix**: Replaced with StandardTokenizerFactory in `managed-schema.xml`
```xml
<tokenizer class="solr.StandardTokenizerFactory"/>
```

**Files Modified**: `retrieval/volume/data/ragcore/conf/managed-schema.xml`

---

### Error 2: Missing Module Libraries
**Error**: Warnings about missing lib directories

**Root Cause**: `solrconfig.xml` referenced non-existent module paths

**Fix**: Commented out lib directives
```xml
<!-- <lib dir="${user.dir}/../modules/langid/lib/" regex=".*\.jar" /> -->
```

**Files Modified**: `retrieval/volume/data/ragcore/conf/solrconfig.xml`

---

### Error 3: Unavailable Update Processors
**Error**: LangDetectLanguageIdentifierUpdateProcessorFactory not found

**Root Cause**: Processors require unavailable modules

**Fix**: Commented out entire langid-detection updateRequestProcessorChain (lines 245-270)

**Files Modified**: `retrieval/volume/data/ragcore/conf/solrconfig.xml`

---

### Error 4: Invalid URLs from Comments
**Error**: `Error downloading file: Invalid URL '# Add Microsoft documentation URLs here'`

**Root Cause**: downloader.py processing comment lines in urls.txt

**Fix**: Added check to skip empty lines and comments
```python
if not url or url.startswith('#'):
    continue
```

**Files Modified**: `retrieval/downloader.py`

---

### Error 5: HTML Instead of Wikitext
**Error**: Downloaded Wikipedia pages were HTML, filter expected wikitext format

**Root Cause**: Standard Wikipedia URLs return HTML

**Fix**: Changed URLs to use `?action=raw` parameter
```
https://en.wikipedia.org/w/index.php?title=Python_(programming_language)&action=raw
```

**Files Modified**: `data/wiki/urls.txt`

---

### Error 6: Wrong Solr Field Name
**Error**: Documents indexed with 'text' field but search looking for 'text_en'

**Root Cause**: solr_handler.py uploading to generic 'text' field

**Fix**: Changed to upload to language-specific field
```python
docs.append({
    "id": filename,
    "title": content.splitlines()[0],
    "text_en": "\n".join(content.splitlines()[1:]),  # Changed from "text"
    "url": url
})
```

**Files Modified**: `retrieval/solr_handler.py:58`

---

### Error 7: Overly Aggressive Score Filtering
**Error**: Search returning 0 results despite Solr finding documents with scores ~0.4-0.6

**Root Cause**: Score threshold calculated as `len(query.split()) * 1` = 3, but actual scores much lower

**Fix**: Changed to more reasonable threshold
```python
# Use a more reasonable threshold (0.1 per query term)
expected_score = len(clear_query.split()) * 0.1 * self.min_score_weight
```

**Files Modified**: `retrieval/solr_handler.py:96`

---

### Error 8: Module Import Error
**Error**: `ModuleNotFoundError: No module named 'client'`

**Root Cause**: Relative imports not working correctly

**Fix**: Changed to explicit relative imports
```python
from .client import LLM_Client  # Changed from "from client import"
```

**Files Modified**:
- `LLM/ollama_client.py:1`
- `LLM/openai_client.py:1`

---

### Error 9: Context Window Overflow
**Error**: Ollama logs showed `truncating input prompt limit=4096 prompt=24475`

**Root Cause**: Wikipedia documents ~65,000 characters exceed 4096 token context window

**Fix**: Limited text to 500 characters with sentence-aware truncation
```python
# Limit text to first 500 characters to avoid context overflow
full_text = best_doc[text_field]
limited_text = full_text[:500]
last_period = limited_text.rfind('.')
if last_period > 100:  # If there's a sentence ending, use it
    limited_text = limited_text[:last_period + 1]
limited_text += ("..." if len(full_text) > len(limited_text) else "")
```

**Files Modified**: `retrieval/solr_handler.py:124-131`

---

### Error 10: Empty Responses with RAG Retrieval (CRITICAL FIX)
**Error**: Questions triggering RAG retrieval returned completely empty responses

**Root Cause**: The `run_query()` method popped the user question from message_history but never added it back. This caused Ollama to receive a conversation ending with a system message instead of a user message.

**Message Flow Before Fix**:
1. System: "You are a tutor..."
2. System: "Answer based on context: <data>"
3. ❌ Missing: User message with the question

**Message Flow After Fix**:
1. System: "You are a tutor..."
2. System: "Answer based on context: <data>"
3. ✅ User: "What is Python?"
4. Assistant: Response generated

**Fix**: Added the user question back to message_history after context injection
```python
# Add the user question back so Ollama receives proper user message
self.message_history.append({"role": "user", "content": last_question})
```

**Files Modified**: `LLM/client.py:83`

---

## Current State

### System Status
- ✅ Solr running at http://localhost:8983
- ✅ Ollama running at http://localhost:11434
- ✅ Streamlit UI running at http://localhost:8501
- ✅ Wikipedia documents indexed (Python, Machine Learning, NLP)
- ✅ RAG pipeline fully functional

### How to Run
```bash
# Start services (if not already running)
docker start solr_docker ollama_docker

# Run the full pipeline
python3 __main__.py --all

# Or run UI only (if data already uploaded)
python3 __main__.py --ui
```

### Testing
Test the RAG system with questions like:
- "What is Python?"
- "What is machine learning?"
- "What is natural language processing?"

The system will retrieve relevant context from Solr and provide informed answers using the Ollama LLM.

---

## Key Lessons Learned

1. **Docker Image Limitations**: Not all Solr plugins are included in docker images - use StandardTokenizerFactory instead of ICU-based tokenizers
2. **Score Thresholds**: Solr scores vary widely - use conservative thresholds like 0.1 per query term
3. **Context Windows**: LLM context limits are real - limit retrieved text to 500 chars to stay within 4096 token limit
4. **Message Structure**: LLMs expect proper role alternation - always end with a user message before generation
5. **Relative Imports**: Python package imports need explicit relative syntax (`.client` not `client`)

---

## Architecture Summary

### Data Flow
1. **Download**: Fetch Wikipedia articles via raw API
2. **Filter**: Extract title and clean content
3. **Upload**: Index documents in Solr with language-specific fields
4. **Query**: User asks question in UI
5. **Retrieve**: Solr searches using edismax with field boosting
6. **Re-rank**: Custom scoring (position + term frequency)
7. **Inject**: Top result added as context to message history
8. **Generate**: Ollama LLM produces contextual response
9. **Stream**: Response streams back to UI

### Key Components
- **Solr**: Document storage and retrieval (edismax parser)
- **Ollama**: Local LLM inference (llama3.2:3b)
- **Streamlit**: Web UI for chat interface
- **Wikipedia**: Knowledge source (via raw API)

### Configuration
- RAG triggering: Questions ending with "?" OR messages >8 words
- Score threshold: 0.1 per query term
- Context limit: 500 characters
- Top N results: 10 (but only best 1 used)
- Languages supported: English, German, Hungarian
