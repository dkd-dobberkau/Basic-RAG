import os
import re
from os.path import join, exists
from pypdf import PdfReader
import wikitextparser as wtp
from bs4 import BeautifulSoup
from typing import Tuple

class DataFilter:
    # returns the title and the content of the article
    def _filter(self, file_path : str)  -> Tuple[str, str]:
        return "", ""
    
    # returns the text content of a pdf
    def _get_pdf_content(self, path : str, max_pages : int = 10) -> list[str]:
        reader = PdfReader(path)
        i = 0
        result : list[str] = [ "" ]

        for page in reader.pages:
            result[-1] += f"\n{page.extract_text()}"
            i += 1

            if(max_pages == i):
                result.append("")
                i = 0

        return result

    # generic html getter
    def _get_html_content(self, path : str) -> str:
        with open(path, encoding='utf-8') as file:
            soup = BeautifulSoup(file, 'html.parser', from_encoding="utf-8")
            return soup.get_text()


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

class MicrosoftDocFilter(DataFilter):
    def __init__(self, start_phrase : str):
        super().__init__()
        self.start_phrase = start_phrase
    
    def _filter(self, path):
        with open(path, encoding='utf-8') as file:
            soup = BeautifulSoup(file, 'html.parser', from_encoding="utf-8")

            # finding html elements by their tags
            article_div = soup.find('div', attrs={'class': 'content'})

            title = article_div.find('h1').text.strip()
            text_containers = article_div.find_all(['p', 'li', 'td', 'th', 'h2', 'h3' ])

            # only using data after 'start phrase ...' (removes unnecessarry data)
            has_started = False

            # uniting all the text content into a single string
            text_content = []

            for element in text_containers:
                if has_started:
                    text_content.append(element.text.strip())
                else:
                    has_started = element.text.strip().startswith(self.start_phrase)

            return title, "\n".join(text_content)

class WikiFilter(DataFilter):
    def __init__(self, urls_for_id : dict[str, str] = {}):
        super().__init__()
        self.urls_for_id = urls_for_id
        self.keep_external_links = True

    def _handle_template(self, template) -> str:
        name : str = template.name.lower()

        if name == 'short description':
            return f'({template.arguments[0].string.removeprefix("|")})\n'
        
        if name.startswith('infobox'):
            return ''.join([f'{arg.name.strip()}: {arg.value}' for arg in template.arguments if arg.name and arg.value != '\n'])
            
        return ''

    def _filter(self, path):
        with open(path, encoding='utf-8') as file:
            file_name = os.path.basename(path)
            
            title = re.findall(r'title=(.*)&', self.urls_for_id[file_name])[0] if file_name in self.urls_for_id else file_name.capitalize()
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
                    if link.text or link.title:
                        replacement = link.text if link.text else link.title
                        section_content = section_content.replace(link.string, replacement)

                if not self.keep_external_links:
                    for link in section.external_links:
                        if link.text or link.url:
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
    def _utf8_encode(self, path : str):
        with open(path, encoding="windows-1250") as file:
            content = file.read()
            
        encoded = content.encode('utf-8')

        with open(path, 'wb') as file:
            file.write(encoded)


    def _filter(self, path):
        soup : BeautifulSoup = None
        
        try:
            with open(path, encoding="utf-8") as file:
                soup = BeautifulSoup(file, 'html.parser')
        except UnicodeDecodeError:
            # change the encoding to utf-8
            self._utf8_encode(path)

            with open(path, encoding="utf-8") as file:
                content = file.read()

            # retry
            soup = BeautifulSoup(content, 'html.parser')
        
        main_content = soup.find('main')

        # finding root of the content
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
        
        print("Processing pdfs this may take a while")

        for filename in os.listdir(input_path):
            if filename == "urls.txt":
                continue

            path = join(input_path, filename)
            extension = filename.split(".")[-1].lower()

            title : str
            content : str

            if extension == "pdf":
                # splitting the pdf into parts
                content = self._get_pdf_content(path)
                title = filename.capitalize().removesuffix(".pdf")
                
                # saving the parts
                for part, text in enumerate(content, start=1):
                    with open(join(output_path, f"{title}_{part}"), 'w', encoding="utf8") as file:
                        file.write(title + "\n" + text)

                continue
            else:
                title, content = self._filter(path)
            
            with open(join(output_path, filename), 'w', encoding="utf8") as file:
                file.write(title + "\n" + content)