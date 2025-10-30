import os
import re
from os.path import exists, join
from pysolr import Solr, SolrError, Results
from typing import Tuple

class SolrHandler:
    def __init__(self, host : str, core : str, min_score_weight : float = 1):
        super().__init__()
        self.host = host
        self.core = core
        self.solr = Solr(self._get_url(), timeout=410)
        self.min_score_weight = min_score_weight

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

                # handling split pdfs
                if url == "":
                    backup = '_'.join(filename.split('_')[:-1]).lower() + ".pdf"
                    url = url_for_data[backup] if backup in url_for_data else ""
                
                # Store in language-specific field for proper text analysis
                docs.append({
                    "id": filename,
                    "title": content.splitlines()[0],
                    "text_en": "\n".join(content.splitlines()[1:]),  # Default to English
                    "url": url
                })

        self.solr.add(docs)

    def search(self, query : str, language : str, top_n : int = 10) -> Tuple[list[str], list[str]]:
        with open(os.path.join(os.path.dirname(__file__), f'./volume/data/ragcore/conf/lang/stopwords_{language}.txt'), 'r', encoding='utf-8') as file:
            stopwords = file.read().splitlines()
        
        clear_query = re.sub(r'[^\w\s]', ' ', query.lower())
        clear_query = " ".join([word for word in clear_query.split() if word not in stopwords])
        text_field = f"text_{language}"

        #* a well setup highlighter could also do the job
        # "hl":"true",
        # "hl.tag.pre":"**",
        # "hl.tag.post":"**",
        # "hl.method":"unified",
        # "hl.usePhraseHighLighter":"false",
        # "hl.highlightMultiTerm":"false",
        # "hl.fragsize": str(frag_size),

        params = {
            "fl":       "score,title,text_en,url,"+text_field,
            "sort":     "score desc",
            "rows":     str(top_n),
            "tie":      "0.1",
            "defType":  "edismax",
            "qf":       f"title^2 {text_field} url",
            "pf":       f"{text_field}^2",
            "stopwords":"true",
        }

        results = self.solr.search(clear_query,**params)

        # filter results based on processed query length and adjusted threshold
        # Use a more reasonable threshold (0.1 per query term)
        expected_score = len(clear_query.split()) * 0.1 * self.min_score_weight
        results.docs = [doc for doc in results.docs if doc['score'] > expected_score]
        
        if len(results) == 0:
            # if no results found, try to search in english
            if language != "en":
                #* translation could be done here
                return self.search(clear_query, "en", top_n)
            else:
                return [], []

        #* correcting the results because of nouns
        scores : list[Tuple] = []

        for index, doc in enumerate(results.docs, start=1):
            score = 500 - index * 50
            text = re.sub(r'[^\w\s]', ' ', doc[text_field].lower())

            for word in text.split():
                if word.strip() in clear_query:
                    score += 1

            ranking : Tuple = (score, doc)
            scores.append(ranking)

        #! right now it's just a single result, but it could return multiple documents
        best_doc = max(scores, key=lambda x: x[0])[1]

        # Limit text to first 500 characters to avoid context overflow
        full_text = best_doc[text_field]
        # Take first 500 chars and try to end at a sentence
        limited_text = full_text[:500]
        last_period = limited_text.rfind('.')
        if last_period > 100:  # If there's a sentence ending, use it
            limited_text = limited_text[:last_period + 1]
        limited_text += ("..." if len(full_text) > len(limited_text) else "")

        best_texts = [
            best_doc['title'] + "\n" + limited_text
        ]

        sources = []

        if 'url' in best_doc:
            sources.append(best_doc['url'])

        return best_texts, sources