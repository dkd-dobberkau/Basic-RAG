import os
from os.path import join, exists
from dotenv import load_dotenv
import sys
from retrieval.downloader import Downloader
from retrieval.filters import DataFilter, MicrosoftDocFilter, WikiFilter, DbFilter
from retrieval.solr_handler import SolrHandler

def main ():
    project_dir = os.path.dirname(__file__)

    # Loading packages
    for package in ['filtering', 'retrieval', 'UI']:
        sys.path.append(join(project_dir, package))

    # Handling data
    data_dir = join(project_dir, 'data')

    if not exists(data_dir):
        print("Missing data folder")
        quit(-1)

    url_for_id = Downloader().download_data(data_dir)

    # *configure your data subfolders here
    data_subfolders = {
        "microsoft": (MicrosoftDocFilter(), "de"),
        "wiki": (WikiFilter(), "en"),
        "db": (DbFilter(), "hu")
    }

    filtered_dir = join(project_dir, 'filtered')
    filter_data(data_dir, filtered_dir, data_subfolders)

    # Uploading the filtered data to Solr
    upload_data(filtered_dir, data_subfolders, url_for_id)

def filter_data(data_dir : str, filtered_dir : str, subfolders : dict[str, tuple[DataFilter, str]]):
    if not exists(filtered_dir):
        os.mkdir(filtered_dir)

    for folder, helpers in subfolders.items():
        helpers[0].process_folder(
            join(data_dir, folder),
            join(filtered_dir, folder)
        ) 

def upload_data(filtered_dir : str, subfolders : dict[str, tuple[DataFilter, str]], urls : dict[str, str]):
    load_dotenv()
    handler = SolrHandler(
        os.environ.get('SOLR_SERVER'), 
        os.environ.get('CORE_NAME')
    )

    if not handler.is_available():
        quit(-1)
    
    for folder, helpers in subfolders.items():
        handler.upload_forlder(
            folder=join(filtered_dir, folder),
            language=helpers[1],
            url_for_data=urls
        )

if __name__ == '__main__':
    main()