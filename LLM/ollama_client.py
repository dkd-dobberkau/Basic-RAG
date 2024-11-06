import os
from ollama import Client, Options
from retrieval.solr_handler import SolrHandler

class OllamaClient:
    def __init__(self, host : str, model : str, solr : SolrHandler):
        #* you could add relevant options based on this article: https://medium.com/@auslei/how-to-use-ollamas-generate-and-chat-functions-4f90eac8d0fd
        # options = Options()

        self.client = Client(host=host)
        
        running : list[dict] = self.client.ps()['models']
        
        if sum(r['name'] == model for r in running) == 0:
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

    def new_message(self, message : str):
        print(message)
        self.message_history.append({"role": "user", "content": message})
        
        stream = self.client.chat(model=self.model, messages=self.message_history, stream=True)
        result = []

        for chunk in stream:
            result.append(chunk['message']['content'])
            yield chunk['message']['content']

        self.message_history.append({"role": "assistant", "content": "".join(result)})
