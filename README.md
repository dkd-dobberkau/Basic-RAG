# NLP ASSIGNMENT 1

### Setup
If you don't have an Apache Solr server already setup I'd recommend using docker to install it.
```bash
docker pull solr
docker run -p 8983:8983 -t solr

# on the container create the core with
bin/solr create -c <YOUR_CORE_NAME> -s 2 -rf 2
```

Then configure the `.env` file according to your setup (in the root folder of this project):
```env
SOLR_SERVER=localhost:8983
CORE_NAME=<YOUR_CORE_NAME>
```