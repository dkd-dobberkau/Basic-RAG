import os
from os.path import join, exists
from dotenv import load_dotenv
import sys
import argparse
from retrieval import Downloader, SolrHandler
from retrieval.filters import DataFilter, MicrosoftDocFilter, WikiFilter, DbFilter
import subprocess
from typing import Optional, Sequence

def main (main_args  : Optional[Sequence[str]] = None):
    project_dir = os.path.dirname(__file__)
    prepare(project_dir)

    parser = argparse.ArgumentParser()
    parser.add_argument('--download', help='Download data', action='store_true', default=False)
    parser.add_argument('--filter', help='Filter data', action='store_true', default=False)
    parser.add_argument('--keep-data', help='Keep the filtered data ater upload', action='store_true', default=False)
    parser.add_argument('--upload', help='Upload data', action='store_true', default=False)
    parser.add_argument('--process-data', help='Only run the first 3 steps without launching the UI', action='store_true', default=False)
    parser.add_argument('--ui', help='Start the UI', action='store_true', default=False)
    parser.add_argument('--all', help='Run all the steps', action='store_true', default=False)

    if(main_args is None or len(main_args) == 0):
        main_args = [ "-h"]

    try:
        args = parser.parse_args(main_args)
    except Exception as error:
        print(error)
        quit(-1)

    data_dir = join(project_dir, 'data')

    url_for_id = {}
    
    # Downloading data
    if args.download or args.process_data or args.all:
        url_for_id = download_data(data_dir)
        print("Downloaded data")

        # save the urls for later use
        with open(join(data_dir, 'urls.json'), 'w', encoding='utf-8') as file:
            file.write(str(url_for_id))
    
    # Load (older) data urls if needed
    elif args.upload:
        if not exists(join(data_dir, 'urls.json')):
            print("Missing urls.json file")
            quit(-1)

        with open(join(data_dir, 'urls.json'), 'r', encoding='utf-8') as file:
            url_for_id = eval(file.read())
    
    #* configure your data subfolders here
    subfolder_processors = {
        "microsoft": MicrosoftDocFilter('Gilt für:'),
        "wiki": WikiFilter(url_for_id),
        "db": DbFilter()
    }

    # Filter data
    filtered_dir = join(project_dir, 'filtered')

    if args.filter or args.process_data or args.all:
        filter_data(data_dir, filtered_dir, subfolder_processors)
        print("Filtered data")

    # Upload data
    if args.upload or args.process_data or args.all:
        solr = SolrHandler(
            os.environ.get('SOLR_SERVER'), 
            os.environ.get('CORE_NAME')
        )
        
        upload_data(solr, filtered_dir, subfolder_processors.keys(), url_for_id)
        print("Uploaded data")
        del solr


    # Clean up
    if exists(filtered_dir) and not args.keep_data:
        for root, dirs, files in os.walk(filtered_dir, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))
        os.rmdir(filtered_dir)

    # free up memory
    del filtered_dir, subfolder_processors, data_dir

    # Setting up chat client
    if args.ui or args.all:
        try:
            proc = subprocess.Popen(f"python3 -m streamlit run {join(project_dir, 'UI/ui.py')} --server.port {os.environ.get('UI_PORT')}", shell=True)
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
    main(sys.argv[1:])