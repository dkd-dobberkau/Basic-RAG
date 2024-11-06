import os
from os.path import join, exists
from dotenv import load_dotenv
import sys
from retrieval import Downloader, SolrHandler
from retrieval.filters import DataFilter, MicrosoftDocFilter, WikiFilter, DbFilter
import subprocess

def main ():
    project_dir = os.path.dirname(__file__)
    prepare(project_dir)

    # Downloading data
    data_dir = join(project_dir, 'data')
    url_for_id = download_data(data_dir)

    # *configure your data subfolders here
    subfolder_processors = {
        "microsoft": MicrosoftDocFilter(),
        "wiki": WikiFilter(),
        "db": DbFilter()
    }

    # Filtering the data
    filtered_dir = join(project_dir, 'filtered')
    filter_data(data_dir, filtered_dir, subfolder_processors)

    # Uploading the filtered data to Solr
    solr = SolrHandler(
        os.environ.get('SOLR_SERVER'), 
        os.environ.get('CORE_NAME')
    )
    
    upload_data(solr, filtered_dir, subfolder_processors.keys(), url_for_id)

    # free up memory
    del solr, filtered_dir, subfolder_processors, data_dir

    # Setting up chat client
    try:
        proc = subprocess.Popen(f"python -m streamlit run {join(project_dir, 'UI/ui.py')} --server.port {os.environ.get('UI_PORT')}")
        proc.wait()
    except KeyboardInterrupt:
        pass
    except Exception as error:
        print(error)

# loading packages and environment variables
def prepare(project_dir : str):
    load_dotenv()

    for package in ['filtering', 'retrieval']:
        sys.path.append(join(project_dir, package))

def download_data(data_dir : str) -> dict[str, str]:
    if not exists(data_dir):
        print("Missing data folder")
        quit(-1)

    return Downloader().download_data(data_dir)

def filter_data(data_dir : str, filtered_dir : str, subfolders : dict[str, DataFilter]):
    if not exists(filtered_dir):
        os.mkdir(filtered_dir)

    for folder, processor in subfolders.items():
        processor.process_folder(
            join(data_dir, folder),
            join(filtered_dir, folder)
        ) 

def upload_data(handler : SolrHandler, filtered_dir : str, subfolders : list[str], urls : dict[str, str]):
    if not handler.is_available():
        quit(-1)
    
    for folder in subfolders:
        handler.upload_forlder(
            folder=join(filtered_dir, folder),
            url_for_data=urls
        )

if __name__ == '__main__':
    main()