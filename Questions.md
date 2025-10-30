# Questions and Answers

## Q1: Where does the RAG response happen in the code?

The RAG response happens across several key locations in three main stages:

### 1. Retrieval Trigger
In `LLM/ollama_client.py:20-29` (and similarly in `openai_client.py:12-21`):

```python
def new_message(self, message : str):
    should_run_query = self.should_run_query(message)

    self.message_history.append({"role": "user", "content": message})

    if should_run_query:
        self.run_query()  # ← This triggers the RAG process
```

### 2. Retrieval & Context Injection
In `LLM/client.py:61-81` - the `run_query()` method:

- **Line 63**: Detects message language
- **Line 71**: Calls `self.solr.search()` to retrieve relevant documents
- **Line 81**: Calls `insert_docs_to_query()` which formats and injects the retrieved context

The key line is **`LLM/client.py:47-52`** where context gets inserted:

```python
def insert_docs_to_query(self, data : str, query : str, sources : list[str] = []):
    self.message_history.append({
        "role": "system",
        "content": self.insertion_format.format(data=data, query=query),
        "sources": sources
    })
```

This uses the format: `"Answer the question based only on the context below: \nContext: {data} \nQuestion: {query}"` (line 22)

### 3. Generation with Augmented Context
Back in `ollama_client.py:31-50` or `openai_client.py:25-40`:

```python
# The message_history now contains: [system prompt, user message, injected context]
stream = self.client.chat(model=self.model, messages=self.message_history, stream=True)
```

The LLM receives the entire conversation history including the injected system message with retrieved documents, so it generates responses based on that augmented context.

**Summary**: The RAG magic happens at `LLM/client.py:61-81` where documents are retrieved and `LLM/client.py:47-52` where they're inserted into the message history before the LLM generates its response.

---

## Q2: How does the Solr response get used and transformed to the LLM?

### Step 1: Solr Returns Raw Documents (`solr_handler.py:91`)

Solr returns documents with these fields:
- `score`, `title`, `text_en`, `url`, `text_{language}`

```python
results = self.solr.search(clear_query, **params)
```

### Step 2: Post-Processing & Re-Ranking (`solr_handler.py:94-120`)

**Line 94-95**: Filter by minimum score threshold
```python
expected_score = len(query.split()) * self.min_score_weight
results.docs = [doc for doc in results.docs if doc['score'] > expected_score]
```

**Line 108-117**: Custom re-ranking algorithm
- Gives position-based scores (500, 450, 400...)
- Adds +1 for each query word found in document text
- Creates list of `(score, doc)` tuples

**Line 120**: Selects single best document
```python
best_doc = max(scores, key=lambda x: x[0])[1]
```

### Step 3: Format Document for LLM (`solr_handler.py:122-130`)

**Line 122-124**: Combine title and text with newline
```python
best_texts = [
    best_doc['title'] + "\n" + best_doc[text_field]
]
```

**Line 126-129**: Extract source URL
```python
sources = []
if 'url' in best_doc:
    sources.append(best_doc['url'])

return best_texts, sources  # Returns: (["Title\nFull text content"], ["https://..."])
```

### Step 4: Inject into Message History (`client.py:71-81`)

**Line 71**: Get results from Solr
```python
found = self.solr.search(query_text, language, 10)
results = found[0]  # ["Title\nContent"]
sources = found[1]  # ["https://..."]
```

**Line 81**: Join multiple results (though currently only one) and inject
```python
self.insert_docs_to_query("\n".join(results), last_question, sources)
```

### Step 5: Template Formatting (`client.py:47-52`)

The retrieved text gets wrapped in the prompt template:
```python
def insert_docs_to_query(self, data : str, query : str, sources : list[str] = []):
    self.message_history.append({
        "role": "system",
        "content": self.insertion_format.format(data=data, query=query),
        "sources": sources
    })
```

Where `insertion_format` (line 22) is:
```
"Answer the question based only on the context below:
Context: {data}
Question: {query}"
```

### Final Result Sent to LLM

The message history becomes:
```python
[
    {"role": "system", "content": "You are a helpful assistant..."},  # Assistant context
    {"role": "user", "content": "What is Python?"},
    {"role": "system", "content": "Answer the question based only on the context below:\nContext: Python Programming\nPython is a high-level...\nQuestion: What is Python?", "sources": ["https://..."]}
]
```

**Summary**: Solr document (`title` + `text_{language}`) → String joined → Template wrapped → Inserted as system message → Sent to LLM with full conversation history.

---

## Q3: How does the re-ranking work?

The re-ranking algorithm uses a **hybrid scoring approach** that combines position-based scoring with term frequency matching.

### Algorithm Breakdown

#### 1. Position-Based Initial Score (`solr_handler.py:109`)
```python
score = 500 - index * 50
```

Each document gets a base score based on its Solr ranking position:
- **1st document**: 500 - (1 × 50) = **450**
- **2nd document**: 500 - (2 × 50) = **400**
- **3rd document**: 500 - (3 × 50) = **350**
- **4th document**: 500 - (4 × 50) = **300**
- ...and so on

This heavily favors Solr's top results but leaves room for reordering.

#### 2. Term Frequency Boost (`solr_handler.py:110-114`)
```python
text = re.sub(r'[^\w\s]', ' ', doc[text_field].lower())

for word in text.split():
    if word.strip() in clear_query:
        score += 1
```

For every word in the document that appears in the query, add **+1** to the score.

**Important**: The query (`clear_query`) has already been processed at `line 67-68`:
- Punctuation removed
- Stopwords filtered out
- Lowercased

**Example**:
- Query: "What is Python programming?"
- After processing: `clear_query = "python programming"`
- Document contains "python" 50 times and "programming" 30 times
- Boost: **+80 points**

#### 3. Select Best Document (`solr_handler.py:120`)
```python
best_doc = max(scores, key=lambda x: x[0])[1]
```

Choose the document with the highest combined score.

### Why This Approach?

The comment on `line 105` says **"correcting the results because of nouns"**. This suggests:

1. **Solr's edismax** might not perfectly weight important nouns/keywords
2. **Term frequency matters**: A document with many query term occurrences is likely more relevant
3. **Position still dominates**: A document needs ~150 extra term matches to jump from 2nd to 1st place

### Real Example

Imagine these Solr results for query `"python django framework"`:

| Rank | Doc | Solr Score | Base Score | "python" count | "django" count | "framework" count | Term Boost | **Final Score** |
|------|-----|------------|------------|----------------|----------------|-------------------|------------|-----------------|
| 1 | A | 8.5 | 450 | 10 | 5 | 3 | +18 | **468** |
| 2 | B | 7.2 | 400 | 45 | 30 | 25 | +100 | **500** ← **Winner** |
| 3 | C | 6.1 | 350 | 5 | 2 | 1 | +8 | **358** |

Document B gets re-ranked to #1 because it contains many more query terms despite being Solr's 2nd choice.

### Potential Issues

1. **No term saturation**: Counting every occurrence linearly can over-reward keyword stuffing
2. **No TF-IDF weighting**: Common words get same weight as rare important terms
3. **Single document only**: Despite re-ranking all docs, only the top one is returned (`line 120`)

This is a simple but effective heuristic for ensuring the most term-dense document reaches the LLM context.

---

## Q4: Is the re-ranking hardcoded or can it be done per query?

The re-ranking algorithm is **mostly hardcoded** with only one configurable parameter.

### Current Configuration

#### Instance-Level Configuration (Constructor)

`solr_handler.py:8`
```python
def __init__(self, host : str, core : str, min_score_weight : float = 1):
    self.min_score_weight = min_score_weight
```

**Only configurable parameter**: `min_score_weight` (default: 1)
- Used at `line 94` for minimum score threshold filtering
- Not used in re-ranking itself
- Current usage: Both instantiations use **default value** (not passed explicitly)

#### Per-Query Parameters

`solr_handler.py:63`
```python
def search(self, query : str, language : str, top_n : int = 10):
```

**`top_n`**: Controls how many documents Solr retrieves initially
- Passed to Solr as `"rows": str(top_n)` at `line 83`
- All retrieved docs go through re-ranking
- Currently always called with **`top_n=10`** from `client.py:71`

### Hardcoded Re-Ranking Values

`solr_handler.py:108-114`
```python
score = 500 - index * 50          # HARDCODED: base=500, penalty=50
for word in text.split():
    if word.strip() in clear_query:
        score += 1                # HARDCODED: +1 per match
```

**Cannot be changed per query or per instance:**
- **Base score**: 500
- **Position penalty**: 50 per rank
- **Term frequency weight**: +1 per occurrence

### To Make It Configurable

You would need to modify the code like this:

```python
class SolrHandler:
    def __init__(self, host, core, min_score_weight=1,
                 rerank_base=500, rerank_penalty=50, term_weight=1):
        self.rerank_base = rerank_base
        self.rerank_penalty = rerank_penalty
        self.term_weight = term_weight

    def search(self, query, language, top_n=10,
               custom_rerank_params=None):  # Per-query override
        # ... in re-ranking loop:
        score = self.rerank_base - index * self.rerank_penalty
        # ...
        score += self.term_weight  # instead of += 1
```

**Answer**: The re-ranking algorithm is **hardcoded** and cannot be adjusted per query without modifying the source code. Only `top_n` (number of docs to retrieve) and `min_score_weight` (filtering threshold) are configurable.
