import pymupdf
from pymupdf4llm import to_markdown
import pypandoc
import panflute
import io
import re
import fitz
import unicodedata
from typing import Dict

def extract_text_lines(pdf_path: str) -> panflute.Doc:
    doc = pymupdf.open(pdf_path)
    markdown = to_markdown(doc)
    pandoc_json = pypandoc.convert_text(markdown, 'json', format='md')
    doc_panflute = panflute.load(io.StringIO(pandoc_json))
    return doc_panflute

def extract_pages(doc: panflute.Doc) -> Dict[str, str]:
    for elem in doc.content:
        if not isinstance(elem, panflute.Para):
            continue

        text = panflute.stringify(elem)
        text = unicodedata.normalize('NFKC', text).replace('\u00A0', ' ')
        #text = text.replace("—", "-").replace("–", "-")

        m = re.search(r'(?:v\.\s*\d+,\s*n\.\s*\d+,\s*p\.\s*(\d+-\d+)|p\.\s*(\d+-\d+))', text)
        if m:
            return {"pages": f"{m.group(1)}"}

    return {}

def extract_pages_fallback(pdf_path: str) -> Dict[str, str]:
    doc = fitz.open(pdf_path)

    for page in doc:
        text = page.get_text().replace("—", "-").replace("–", "-")
        m = re.search(r'\b(\d+)-(\d+)\b', text)
        if m:
            return {"pages": f"{m.group(1)}-{m.group(2)}"}

    return {}

def extract_bibliographic_data(pdf_path: str) -> Dict[str, str]:
    doc = extract_text_lines(pdf_path)

    data = {}
    data.update(extract_pages(doc))

    if "pages" not in data:
        data.update(extract_pages_fallback(pdf_path))

    return data
