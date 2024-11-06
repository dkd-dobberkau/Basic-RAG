import os
from ollama import Client, Options
from retrieval.solr_handler import SolrHandler
from langdetect import detect
from pysolr import Results
import math

class OllamaClient:
    def __init__(self, host : str, model : str, solr : SolrHandler):
        super().__init__()
        #* you could add relevant options based on this article: https://medium.com/@auslei/how-to-use-ollamas-generate-and-chat-functions-4f90eac8d0fd
        # options = Options()

        self.client = Client(host=host)
        
        running : list[dict] = self.client.ps()['models']
        
        if sum(model in r['name'] for r in running) == 0:
            print(f"This model isn't running! Try `docker exec -it ollama_docker ollama run {model}`")

        self.model = model
        self.solr = solr
        self.message_history : list[dict[str, str]] = []

        dirname = os.path.dirname(__file__)
        self.contexts_dir = os.path.join(dirname, "contexts")
        self.assistants = [filename.removesuffix('.txt') for filename in os.listdir(self.contexts_dir) if filename.endswith('.txt')]
    
    def _get_prompt(self, assistant : str):
        if assistant not in self.assistants:
            return ""
        
        with open(f"{self.contexts_dir}/{assistant}.txt", "r", encoding="utf-8") as file:
            return file.read()
    
    def new_chat(self, assistant : str):
        self.message_history = [
            {"role": "system", "content": self._get_prompt(assistant) }    
        ]

    def insert_data_to_context(self, data : str, question : str, sources : list[str] = []):
        self.message_history.append({
            "role": "system", 
            "content": f"Answer the question based only on the context below: \nContext: {data} \nQuestion: {question}",
            "sources": sources
        })

    def run_query(self):
        last_question = self.message_history.pop()['content']
        
        language = detect(last_question)

        if language not in ['en', 'de', 'hu']:
            language = 'en'
        
        found = self.solr.search(last_question.strip().removesuffix('?'), language, 10)

        result = found[0]
        source = found[1]
        
        self.insert_data_to_context(result if len(result) != "" else "No data found", last_question, [source])


    def new_message(self, message : str):
        self.message_history.append({"role": "user", "content": message})

        # if it's a question or a long message we should run a query
        if message.endswith("?") or len(message.split(' ')) > 4:
            self.run_query()

        stream = self.client.chat(model=self.model, messages=self.message_history, stream=True)

        response = []

        for chunk in stream:
            response.append(chunk['message']['content'])
            yield chunk['message']['content']
            
        #* There was an implementation where the LLM generated queries too
        #* but it should be a separate one which would cause performance issues

        self.message_history.append({"role": "assistant", "content": "".join(response)})