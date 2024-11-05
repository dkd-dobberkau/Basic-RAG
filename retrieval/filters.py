import os
from os.path import join, exists
from pypdf import PdfReader
from typing import Tuple

class DataFilter:
    # returns the title and the content of the article
    def _filter(self, file_path : str)  -> Tuple[str, str]:
        return "", ""
    
    # returns the text content of a pdf
    def _get_pdf_content(self, path):
        reader = PdfReader(path)
        return [page.extract_text() for page in reader.pages].join("\n")

    """
    filters the input path and puts it to the output (creates the output folder if it is missing
    """
    def process_folder(self, input_path : str, output_path : str):
        if not exists(input_path):
            print(f"{input_path} doesn't exist so it can't be processed")
            return
        
        if not exists(output_path):
            os.mkdir(output_path)
        
        for filename in os.listdir(input_path):
            if filename == "urls.txt":
                continue
            
            path = join(input_path, filename)
    
            title, content = self._filter(path)

            with open(join(output_path, filename), 'w', encoding="utf-8") as file:
                file.write(title + "\n" + content)

from bs4 import BeautifulSoup

class MicrosoftDocFilter(DataFilter):
    def _filter(self, path):
        with open(path, encoding='utf-8') as file:
            soup = BeautifulSoup(file, 'html.parser', from_encoding="utf-8")

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
        

import re
import wikitextparser as wtp

class WikiFilter(DataFilter):
    def _handle_template(self, template) -> str:
        name : str = template.name.lower()

        if name == 'short description':
            return f'({template.arguments[0].string.removeprefix("|")})\n'
        
        if name.startswith('infobox'):
            return ''.join([f'{arg.name.strip()}: {arg.value}' for arg in template.arguments if arg.name and arg.value != '\n'])
            
        return ''

    def _filter(self, path):
        with open(path) as file:
            title = re.findall(r'title=(.*)&', path)[0]
            content = file.read()
            parsed = wtp.parse(content)

            # remove tags and reparse
            content = parsed.string
            for tag in parsed.get_tags():
                content = content.replace(tag.string, tag.contents)
            
            parsed = wtp.parse(content)
            result = ''

            # processing sections
            for section in parsed.sections:
                section_title = section.title

                # skipping unnecessary sections
                if  section_title:
                    if section_title.lower() in ['see also', 'references', 'external links', 'further reading', 'notes']:
                        continue
                    result += f'\n{section_title}\n'

                section_content : str = section.contents.strip()
                
                # handling templates
                for template in section.templates:
                    section_content = section_content.replace(template.string, self._handle_template(template))

                # getting link texts
                for link in section.wikilinks:
                    replacement = link.text if link.text else link.title
                    section_content = section_content.replace(link.string, replacement)

                for link in section.external_links:
                    replacement = link.text if link.text else link.url
                    section_content = section_content.replace(link.string, replacement)

                # removing comments
                for comment in section.comments:
                    section_content = section_content.replace(comment.string, '')

                # we shouldn't change the tables based on this article:
                # https://arxiv.org/html/2402.17944v2

                section_content = section_content.replace("\n===", "\n").replace("===\n", "\n").replace("\n==", "\n").replace("==\n", "\n")
                result +=  section_content + '\n'

            return title, result.strip()

class DbFilter(DataFilter):
    def _filter(self, path):
        with open(path, encoding="utf-8") as file:
            soup = BeautifulSoup(file, 'html.parser')

            # finding root of the content
            main_content = soup.find('main')

            if not main_content or not main_content.find('h1'):
                print(path)

            # gets the first h1 as the title
            title =  main_content.find('h1').text.strip()
            text_containers = main_content.find_all(['p', 'li', 'td', 'th', 'h1', 'h2', 'h3', 'h4' ])

            # only using data after the title
            has_started = False

            # uniting all the text content into a single string
            text_content = []

            for element in text_containers:
                if has_started:
                    text_content.append(element.text.strip())
                else:
                    has_started = element.text.strip() == title

            return title, "\n".join(text_content)
        
    def process_folder(self, input_path : str, output_path : str):
        if not exists(input_path):
            print(f"{input_path} doesn't exist so it can't be processed")
            return
        
        if not exists(output_path):
            os.mkdir(output_path)
        
        for filename in os.listdir(input_path):
            if filename == "urls.txt":
                continue

            path = join(input_path, filename)
            extension = filename.split(".")[-1].lower()

            title : str
            content : str

            if extension == "pdf":
                title = filename.capitalize().removesuffix(".pdf")
                content = self._get_pdf_content(path)
            else:
                title, content = self._filter(path)

            out_filename = title.replace(' ', '_').replace(' ', '_').lower() + '.txt'
            with open(join(output_path, out_filename), 'w', encoding="utf8") as file:
                file.write(title + "\n" + content)