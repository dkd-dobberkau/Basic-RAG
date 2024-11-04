import os
from os.path import join, exists
from dotenv import load_dotenv
import sys
import requests
from filtering.filters import DataFilter, MicrosoftDocFilter, WikiFilter, DbFilter
from solr.handler import SolrHandler

def main ():
    project_dir = os.path.dirname(__file__)

    # Loading packages
    for package in ['filtering', 'solr', 'UI']:
        sys.path.append(join(project_dir, package))

    # Handling data
    data_dir = join(project_dir, 'data')

    if not exists(data_dir):
        print("Missing data folder")
        quit(-1)

    url_for_id = download_data(data_dir)

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

def _download(url : str, out : str, out_path : str, verbose = False) -> bool:
    extension = ".pdf" if url.lower().endswith(".pdf") else ""
    file_path = join(out_path, f"{out}{extension}")

    try:
        response = requests.get(url=url, stream=True)
        response.raise_for_status()  # Check if the request was successful
        with open(file_path, "wb") as file:
            for chucnk in response.iter_content(chunk_size=8192):
                file.write(chucnk)
        return True
    except requests.RequestException as error:
        print(f"Error downloading file: {error}")
        return False

def download_data(data_dir : str) -> dict[str, str]:
    url_for_id = {}

    for folder in os.listdir(data_dir):
        subdirectory = join(data_dir, folder)
        link_path = join(subdirectory, "urls.txt")
        
        if not exists(link_path):
            continue
    
        i = 1

        with open(link_path, 'r', encoding='utf-8') as file:
            for url in file:
                id = f"{folder}_{i}"
                download_success = _download(url, id, subdirectory)
                
                if download_success:
                    url_for_id[id] = url
            i += 1
    return url_for_id


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