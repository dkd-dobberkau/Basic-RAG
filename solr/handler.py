import os
from os.path import exists, join
from pysolr import Solr, SolrError

class SolrHandler:
    def __init__(self, url : str, project : str):
        self.solr = Solr(f"http://{url}/solr/{project}", timeout=10)
    
    def is_connected(self) -> bool:
        try:
            self.solr.ping()
            print("Connected to server")
            return True
        except SolrError:
            print("Connection error")
        return False
    
    def upload_forlder(self, folder : str, language : str):
        if not exists(folder):
            print(f"{folder} doesn't exist so it can't be processed")
            return

        docs : list[dict] = []

        for filename in os.listdir(folder):
            is_pdf = filename.split('.')[-1].lower() == 'pdf'

            with open(join(folder, filename), 'r', encoding='utf-8') as file:
                if is_pdf:
                    return # TODO handle pdf upload

                content = file.read()
                docs.append({
                    "id": filename,
                    # todo
                })

        self.solr.add(content)
