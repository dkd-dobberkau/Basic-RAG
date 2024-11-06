import requests
import os
from os.path import join, exists

class Downloader:
    def _download(self, url : str, out : str, out_path : str) -> bool:
        file_path = join(out_path, out)

        try:
            headers = {'User-Agent': 'Mozilla', 'Accept-Charset': 'utf-8'}
            response = requests.get(url=url, headers=headers)
            response.raise_for_status()  # Check if the request was successful
            response.encoding = 'utf-8'
            
            with open(file_path, "wb") as file:
                for chunk in response.iter_content(chunk_size=8192):
                    file.write(chunk)
            return True
        except requests.RequestException as error:
            print(f"Error downloading file: {error}")
            return False
        except Exception as error:
            print(f"Error: {error}")
            return False

    def download_data(self, data_dir : str) -> dict[str, str]:
        url_for_id = {}

        for folder in os.listdir(data_dir):
            subdirectory = join(data_dir, folder)
            link_path = join(subdirectory, "urls.txt")
            
            if not exists(link_path):
                continue
        
            i = 1

            with open(link_path, 'r', encoding='utf-8') as file:
                for url in file:
                    url = url.strip()
                    id = f"{folder}_{i}"

                    if url.lower().endswith(".pdf"):
                        id = f"{url.split('/')[-1].lower()}"
                    else:
                        i += 1
                    
                    download_success = self._download(url, id, subdirectory)
                    
                    if download_success:
                        url_for_id[id] = url
        return url_for_id
