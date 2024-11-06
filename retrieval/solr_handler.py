import os
import re
from os.path import exists, join
from pysolr import Solr, SolrError, Results
from typing import Tuple

class SolrHandler:
    def __init__(self, host : str, core : str):
        super().__init__()
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

                url = url_for_data[filename] if filename in url_for_data else ""

                if url == "":
                    backup = '_'.join(filename.split('_')[:-1])
                    url = url_for_data[backup] if backup in url_for_data else ""
                
                docs.append({
                    "id": filename,
                    "title": content.splitlines()[0],
                    "text": "\n".join(content.splitlines()[1:]),
                    "url": url_for_data[filename] if filename in url_for_data else ""
                })

        self.solr.add(docs)

    def search(self, query : str, language : str, top_n : int = 10) -> Tuple[str, str]:
        with open(os.path.join(os.path.dirname(__file__), f'./volume/data/ragcore/conf/lang/stopwords_{language}.txt'), 'r', encoding='utf-8') as file:
            stopwords = file.read().splitlines()
        
        clear_query = re.sub(r'[^\w\s]', ' ', query.lower())
        clear_query = " ".join([word for word in clear_query.split() if word not in stopwords])
        text_field = f"text_{language}"

        ''' a well setup highlighter could also do the job
        "hl":"true",
        "hl.tag.pre":"**",
        "hl.tag.post":"**",
        "hl.method":"unified",
        "hl.usePhraseHighLighter":"false",
        "hl.highlightMultiTerm":"false",
        "hl.fragsize": str(frag_size),
        '''

        params = {
            "fl":f"id,title,text_en,url,"+text_field,
            "sort":"score desc",
            "rows": str(top_n),
            "tie":"0.1",
            "defType":"edismax",
            "qf":f"title^1 {text_field}^5",
            "pf":f"{text_field}^2",
            "stopwords":"true",
        }

        results = self.solr.search(clear_query,**params)
        
        if len(results) == 0 and language != "en":
            #* if there was a field with translations it would help a lot
            return self.search(query, "en", top_n)

        scores : list[Tuple] = []

        #* this could be improved by embeddings but sometimes the nouns wouldn't have the expected distance
        for index, doc in enumerate(results.docs, start=1):
            score = 500 - index * 50
            text = re.sub(r'[^\w\s]', ' ', doc[text_field].lower())

            for word in text.split():
                if word.strip() in clear_query:
                    score += 1

            ranking : Tuple = (score, doc)
            scores.append(ranking)

        best = max(scores, key=lambda x: x[0])
        return best[1]['title'] + "\n" + best[1][text_field], best[1]['url'] if best[1]['url'] != "" else best[1]['id']