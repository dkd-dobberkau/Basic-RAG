import os
from os.path import join, exists
import sys
import typing

project_dir = os.path.dirname(__file__)

for package in ['filtering', 'solr', 'UI']:
    sys.path.append(join(project_dir, package))

from filtering.filters import DataFilter, MicrosoftDocFilter, WikiFilter, DbFilter


# Filtering data
data_dir = join(project_dir, 'data')

if not exists(data_dir):
    print("Missing data folder")
    quit(-1)

filtered_dir = join(project_dir, 'filtered')

if not exists(filtered_dir):
    os.mkdir(filtered_dir)

processed_subfolders : dict[str, DataFilter] = {
    "microsoft": MicrosoftDocFilter(),
    "wiki": WikiFilter(),
    "db": DbFilter()
}

for folder, processor in processed_subfolders.items():
    processor.process_folder(
        join(data_dir, folder),
        join(filtered_dir, folder)
    )
    

# Uploading data to apache solr
# TODO

# Creating the search system
# TODO 
