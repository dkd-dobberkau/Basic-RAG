import os
from retrieval.solr_handler import SolrHandler
from langdetect import detect
from typing import Any, Generator

class LLM_Client:
    def __init__(self, solr : SolrHandler, insertion_format = None, use_explicit_query = False):
        super().__init__()
        self.solr = solr

        self.message_history : list[dict[str, str]] = []

        self.contexts_dir : str = "" 
        self.assistants : list[str] = []

        self.load_assistant_names()

        if insertion_format:
            self.insertion_format = insertion_format
        else:
            # based on: https://github.com/ibm-ecosystem-engineering/SuperKnowa/blob/main/4.%20In-context%20learning%20using%20LLM/LLMQnA.py
            self.insertion_format = "Answer the question based only on the context below: \nContext: {data} \nQuestion: {query}"
        
        self.use_explicit_query = use_explicit_query

    # loads all the assistant names from the contexts directory
    def load_assistant_names(self):
        if self.contexts_dir == "":
            dirname = os.path.dirname(__file__)
            self.contexts_dir = os.path.join(dirname, "contexts")
        
        self.assistants = [filename.removesuffix('.txt') for filename in os.listdir(self.contexts_dir) if filename.endswith('.txt')]

    # returns the context prompt for the assistant
    def _get_context_prompt(self, assistant : str):
        if assistant not in self.assistants:
            return ""
        
        with open(f"{self.contexts_dir}/{assistant}.txt", "r", encoding="utf-8") as file:
            return file.read()
        
    def new_chat(self, assistant : str):
        self.message_history = [
            {"role": "system", "content": self._get_context_prompt(assistant) }    
        ]

    def insert_docs_to_query(self, data : str, query : str, sources : list[str] = []):
        self.message_history.append({
            "role": "system", 
            "content": self.insertion_format.format(data=data, query=query),
            "sources": sources
        })

    def should_run_query(self, message : str) -> bool:
        if not self.use_explicit_query:
            # if it's a question or a long message 
            return message.endswith('?') or len(message.split(' ')) > 8
        else:
            return message.startswith("/query")

    def run_query(self):
        last_question = self.message_history.pop()['content']
        language = detect(last_question)

        if language not in ['en', 'de', 'hu']:
            language = 'en'

        # trying to remove unnecessarry characters
        query_text = last_question.strip().removesuffix('?')

        found = self.solr.search(query_text, language, 10)

        results = found[0]
        sources = found[1]

        if len(results) == 0:
            #! sometimes this may not fit the prompt format
            self.insert_docs_to_query("No data found", last_question, [])
        else:
            self.insert_docs_to_query("\n".join(results), last_question, sources)

        # Add the user question back so Ollama receives proper user message
        self.message_history.append({"role": "user", "content": last_question})

    def new_message(self, message : str) -> Generator[Any, Any, None]:
        # override this method in the child class
        pass