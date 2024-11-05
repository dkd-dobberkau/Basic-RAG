import os
import asyncio
from ollama import Client, AsyncClient, Options
from retrieval.solr_handler import SolrHandler

class OllamaClient:
    def __init__(self, host : str, model : str, solr : SolrHandler):
        #* you could add relevant options based on this article: https://medium.com/@auslei/how-to-use-ollamas-generate-and-chat-functions-4f90eac8d0fd
        # options = Options()

        # self.client = Client(host=host)

        self.client = AsyncClient(host=host)
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
    

    async def new_message(self, message : str):
        self.message_history.append({"role": "user", "content": message})
        async for part in await AsyncClient().chat(model=self.model, messages=[message], stream=True):
            print(part['message']['content'], end='', flush=True)
    
    #def new_message(self, message : str) -> str:
    #    self.message_history.append({"role": "user", "content": message})
    #    response = self.client.chat(self.model, messages=self.message_history)
    #    self.message_history.append({"role": "assistant", "content": response['message']['content'] })
    #    return response['message']['content']