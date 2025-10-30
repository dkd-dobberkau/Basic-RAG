from .client import LLM_Client
from openai import OpenAI
from retrieval.solr_handler import SolrHandler

class OpenAI_Client(LLM_Client):
    def __init__(self, api_key: str, model: str, solr: SolrHandler, insertion_format=None, use_explicit_query=False):
        super().__init__(solr, insertion_format, use_explicit_query)

        self.openai = OpenAI(api_key=api_key)
        self.model = model

    def new_message(self, message: str):
        should_run_query = self.should_run_query(message)

        if self.use_explicit_query:
            message = message.removeprefix("/query")

        self.message_history.append({"role": "user", "content": message})

        if should_run_query:
            self.run_query()

        response = []

        stream = self.openai.chat.completions.create(
            model=self.model,
            messages=[
                # removing sources
                {"role": m["role"], "content": m["content"]} for m in self.message_history
            ],
            stream=True
        )

        for chunk in stream:
            content = chunk.choices[0].delta.content
            
            if content:
                response.append(content)
                yield content 

        self.message_history.append({"role": "assistant", "content": "".join(response)})
