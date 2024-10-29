import os
from bs4 import BeautifulSoup
from typing import Tuple

# returns the main text of the article
def process_microsoft_html(path : str) -> Tuple[str, str]:
    with open(path) as file:
        soup = BeautifulSoup(file, 'html.parser')

        # finding html elements by their tags
        article_div = soup.find('div', attrs={'class': 'content'})

        title = article_div.find('h1').text.strip()
        text_containers = article_div.find_all(['p', 'li', 'td', 'th', 'h2', 'h3' ])

        # only using data after 'Gilt für: ...' (removes metadata)
        has_started = False

        # uniting all the text content into a single string
        text_content = []

        for element in text_containers:
            if has_started:
                text_content.append(element.text.strip())
            else:
                has_started = element.text.strip().startswith('Gilt für:')

        return title, "\n".join(text_content)

current_dir = os.path.dirname(__file__)
in_dir = os.path.join(current_dir, '../data/microsoft') 
out_dir = os.path.join(current_dir, '../filtered/microsoft')

if not os.path.exists(out_dir):
    os.mkdir(out_dir)


for filename in os.listdir(in_dir):
    path = os.path.join(in_dir, filename)
    
    title, content = process_microsoft_html(path)

    out_filename = title.replace(' ', '_').replace(' ', '_').lower() + '.txt'
    with open(os.path.join(out_dir, out_filename), 'w') as file:
        file.write(title + "\n" + content)
