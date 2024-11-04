# NLP ASSIGNMENT 1

### Installation
1. Install [git](https://git-scm.com/downloads) and [docker](https://docs.docker.com/engine/install/)
2. Clone this repository and navigate into the root directory:
```bash
git clone https://github.com/Kristof-me/NLP-assignments
cd /path/to/NLP-assignments
```
3. Set up docker:
    - *Note: Turning off security manager could expose your system to security risks. For production versions please setup authentication and java policies which allow scripts to run.*
```bash
docker pull solr
docker create --name solr_server -v ./solr/volume:/var/solr -p 8983:8983 -e SOLR_SECURITY_MANAGER_ENABLED=false solr 
docker start solr_server
```
4. Reload the core by visiting [http://localhost:8983/solr/admin/cores?action=RELOAD&core=ragcore](http://localhost:8983/solr/admin/cores?action=RELOAD&core=ragcore)
5. Configure a `.env` file in the root directory:
```env
SOLR_SERVER=localhost:8983
CORE_NAME=ragcore
```

<!--`docker exec -u root -t -i solr_server /bin/bash`, don't forget to update rhino-->
