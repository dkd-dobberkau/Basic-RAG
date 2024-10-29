import os
import re
from typing import Tuple
import wikitextparser as wtp
from prettytable import PrettyTable

def handle_template(template) -> str:
    name : str = template.name.lower()

    if name == 'short description':
        return f'({template.arguments[0].string.removeprefix("|")})\n'
    
    if name.startswith('infobox'):
        return ''.join([f'{arg.name.strip()}: {arg.value}' for arg in template.arguments if arg.name and arg.value != '\n'])
        
    return ''

def process_wiki_data(path : str) -> Tuple[str, str]:
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
                section_content = section_content.replace(template.string, handle_template(template))

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

            # handling tables
            for table in section.tables:
                ascii_table = PrettyTable()
                data = table.data()

                if len(data) == 0:
                    continue

                ascii_table.field_names = data[0]

                for row in data[1:]:
                    ascii_table.add_row(row)

                print(ascii_table.get_string())

                # for some reason, the table is not being replaced properly
                section_content = section_content.replace(table.string, ascii_table.get_string())

            section_content = section_content.replace("\n===", "\n").replace("===\n", "\n").replace("\n==", "\n").replace("==\n", "\n")
            result +=  section_content + '\n'

        return title, result.strip()

current_dir = os.path.dirname(__file__)
in_dir = os.path.join(current_dir, '../data/wiki') 
out_dir = os.path.join(current_dir, '../filtered/wiki')

if not os.path.exists(out_dir):
    os.mkdir(out_dir)

for filename in os.listdir(in_dir):
    path = os.path.join(in_dir, filename)
    title, content = process_wiki_data(path)

    out_filename = title.replace(' ', '_').replace(' ', '_').lower() + '.txt'

    with open(os.path.join(out_dir, out_filename), 'w') as file:
        file.write(title + "\n" + content)
