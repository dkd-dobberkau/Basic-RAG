# NLP ASSIGNMENT 1

### Installation
1. Install [git](https://git-scm.com/downloads) and [docker](https://docs.docker.com/engine/install/)
2. Clone this repository and navigate into the root directory:
```bash
git clone https://github.com/Kristof-me/NLP-assignments
cd /path/to/NLP-assignments
```
3. Set up docker for solr:
    - *Note: Turning off security manager could expose your system to security risks. For production versions please setup authentication and java policies which allow scripts to run.*
```bash
docker pull solr
docker create --name solr_server -v ./retrieval/volume:/var/solr -p 8983:8983 -e SOLR_SECURITY_MANAGER_ENABLED=false solr 
docker start solr_server
```
4. Reload the core by visiting [http://localhost:8983/solr/admin/cores?action=RELOAD&core=ragcore](http://localhost:8983/solr/admin/cores?action=RELOAD&core=ragcore)
5. Select and setup your model:
```bash
docker pull ollama/ollama
docker create --name ollama_docker --restart unless-stopped -v  ./LLM/ollama:/root/.ollama -p 11434:11434 -e OLLAMA_KEEP_ALIVE=24h -e OLLAMA_HOST=0.0.0.0 ollama/ollama 
docker start ollama_docker

# to setup nvidia support checkout https://hub.docker.com/r/ollama/ollama
# select a model here: https://ollama.com/library
docker exec -it ollama_docker ollama run <model_name>
```
6. Configure a `.env` file in the root directory:
```env
SOLR_SERVER=localhost:8983
CORE_NAME=ragcore
OLLAMA_SERVER=localhost:11434
OLLAMA_MODEL=<model_name:details>
UI_PORT=8501
```

7. Install packages: (python 3.9 is required for streamlit)
```bash
pip install python-dotenv ollama beautifulsoup4 pypdf pysolr wikitextparser streamlit langdetect
```

<!--`docker exec -u root -t -i solr_server /bin/bash`, don't forget to update rhino-->