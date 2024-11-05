import os
from os.path import exists, join
from pysolr import Solr, SolrError

class SolrHandler:
    def __init__(self, host : str, core : str):
        self.host = host
        self.core = core
        self.solr = Solr(self._get_url(), timeout=10)

    def _get_url(self, core : str = '') -> str:
        return f"http://{self.host}/solr/{core if core != '' else self.core}"
    
    def is_available(self) -> bool:
        try:
            # check the dashboard
            self.solr.url = self._get_url('#')
            self.solr.ping()

            # reset the url
            self.solr.url = self._get_url()

            print("Connected to server")
            return True
        except SolrError as error:
            print(error)
        return False
    
    def upload_forlder(self, folder : str, url_for_data : dict[str, str]):
        if not exists(folder):
            print(f"{folder} doesn't exist")
            return

        docs : list[dict] = []

        for filename in os.listdir(folder):
            if filename == "urls.txt":
                continue

            with open(join(folder, filename), 'r', encoding='utf-8') as file:
                content = file.read()
                
                docs.append({
                    "id": filename,
                    "title": content.splitlines()[0],
                    "text": "\n".join(content.splitlines()[1:]),
                    "url": url_for_data[filename] if filename in url_for_data else ""
                })

        self.solr.add(docs)
