import os
from os.path import join, exists
from dotenv import load_dotenv
import sys
import typing

project_dir = os.path.dirname(__file__)

# Adding packages
for package in ['filtering', 'solr', 'UI']:
    sys.path.append(join(project_dir, package))

from filtering.filters import DataFilter, MicrosoftDocFilter, WikiFilter, DbFilter
from solr.handler import SolrHandler


# Filtering data
data_dir = join(project_dir, 'data')

if not exists(data_dir):
    print("Missing data folder")
    quit(-1)

filtered_dir = join(project_dir, 'filtered')

if not exists(filtered_dir):
    os.mkdir(filtered_dir)

subfolders : dict[str, tuple[DataFilter, str]] = {
    # *configure your data folders here
    "microsoft": (MicrosoftDocFilter(), "de"),
    "wiki": (WikiFilter(), "en"),
    "db": (DbFilter(), "hu")
}

for folder, helpers in subfolders.items():
    helpers[0].process_folder(
        join(data_dir, folder),
        join(filtered_dir, folder)
    ) 

# Uploading data to apache solr
load_dotenv()
handler = SolrHandler(
    os.environ.get('SOLR_SERVER'),
    os.environ.get('CORE_NAME')
)

if not handler.is_connected():
    quit(-1)

for folder, helpers in subfolders.items():
    handler.upload_forlder(
        folder=join(filtered_dir, folder),
        language=helpers[1]
    )

# Creating the search system
# TODO 
# handler.solr.search(...)
