from .client import LLM_Client
from ollama import Client, Options
from retrieval.solr_handler import SolrHandler

class OllamaClient(LLM_Client):
    def __init__(self, host : str, model : str, solr : SolrHandler, insertion_format = None, use_explicit_query = False):
        super().__init__(solr, insertion_format, use_explicit_query)
        #* you could add relevant options based on this article: https://medium.com/@auslei/how-to-use-ollamas-generate-and-chat-functions-4f90eac8d0fd
        # options = Options()

        self.client = Client(host=host)
        self.model = model

        # check if the model is running
        running : list[dict] = self.client.ps()['models']
        
        if sum(model in r['name'] for r in running) == 0:
            print(f"This model isn't running! Try `docker exec -it ollama_docker ollama run {model}`")

    def new_message(self, message : str):
        should_run_query =  self.should_run_query(message)

        if self.use_explicit_query:
            message = message.removeprefix("/query")

        self.message_history.append({"role": "user", "content": message})

        if should_run_query:
            self.run_query()

        stream = self.client.chat(model=self.model, messages=self.message_history, stream=True)

        response = []

        for chunk in stream:
            content = chunk['message']['content']

            # Yield all content (llama3.2 doesn't need header filtering)
            response.append(content)
            yield content

        self.message_history.append({"role": "assistant", "content": "".join(response)})