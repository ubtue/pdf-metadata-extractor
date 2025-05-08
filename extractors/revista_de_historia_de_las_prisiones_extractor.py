import pymupdf
from pymupdf4llm import to_markdown
import pypandoc
import panflute
import io
import re
from typing import Dict

SPANISH_KEYWORDS = ["palabras clave", "palavras-chave"]
ENGLISH_KEYWORDS = ["keywords", "key words", "keyword", "key-words"]
ABSTRACTS = ["resumen", "abstract", "resumo"]
NON_NAME_WORDS = ['universidad', 'institución', 'argentina', 'institute', 'nacional', 'departamento', 'buenos aires', 'ciudad', 'méxico', 'entrevista']


def extract_text_lines(pdf_path: str) -> panflute.elements.Doc:
    doc = pymupdf.open(pdf_path)
    markdown = to_markdown(doc)
    pandoc_json = pypandoc.convert_text(markdown, 'json', format='md')
    doc_panflute = panflute.load(io.StringIO(pandoc_json))
    return doc_panflute


def extract_title(doc: panflute.elements.Doc) -> Dict[str, str]:
    title = None
    is_review = False

    for elem in doc.content:
        if isinstance(elem, panflute.Para):
            text = panflute.stringify(elem)
            if re.search(r'\bRESEÑAS?\b', text, re.IGNORECASE):
                is_review = True

    for elem in doc.content:
        if isinstance(elem, panflute.Header):
            if is_review and elem.level == 2:
                title = panflute.stringify(elem).strip()
                break
            elif not is_review and elem.level == 1:
                title = panflute.stringify(elem).strip()
                break

    return {"title": title} if title else {}

def extract_keywords(doc: panflute.elements.Doc) -> Dict[str, str]:
    data = {}
    next_is_keywords_es = False
    next_is_keywords_en = False

    for elem in doc.content:
        if not isinstance(elem, panflute.Para):
            continue

        text = panflute.stringify(elem).strip()
        text_lower = text.lower()

        if next_is_keywords_es and "keywords_es" not in data:
            data["keywords_es"] = text.replace(';', ',')
            next_is_keywords_es = False
            continue

        if next_is_keywords_en and "keywords_en" not in data:
            data["keywords_en"] = text.replace(';', ',')
            next_is_keywords_en = False
            continue

        if any(keyword in text_lower for keyword in SPANISH_KEYWORDS):
            next_is_keywords_es = True
        elif any(keyword in text_lower for keyword in ENGLISH_KEYWORDS):
            next_is_keywords_en = True

    return data

def extract_metadata(doc: panflute.elements.Doc) -> Dict[str, str]:
    data = {}

    for elem in doc.content:
        if not isinstance(elem, panflute.Para):
            continue

        text = panflute.stringify(elem).strip()

        if "tags" not in data and re.search(r'\bRESEÑAS?\b', text, re.IGNORECASE):
            data["tags"] = "RezensionsTagPica"

        if "issn" not in data:
            m = re.search(r'(?i)ISSN[:\s]*([\d]{4}-[\d]{4})', text)
            if m:
                data["issn"] = m.group(1)

        m = re.search(r'nº\s*(\d+)\s*\(([^)]+?\d{4})\)', text, re.IGNORECASE)
        if m:
            data["volume"] = m.group(1).strip()
            data["publishing_date"] = m.group(2).strip()

        m = re.search(r'pp\.\s*(\d+)[–-](\d+)', text, re.IGNORECASE)
        if m:
            data["pages"] = f"{m.group(1)}-{m.group(2)}"

    return data

def extract_abstracts(doc: panflute.elements.Doc) -> Dict[str, str]:
    data = {}
    next_is_abstract_es = False
    next_is_abstract_en = False

    for elem in doc.content:
        if not isinstance(elem, panflute.Para):
            continue

        text = panflute.stringify(elem).strip()

        if next_is_abstract_es and "abstract_es" not in data:
            data["abstract_es"] = text
            next_is_abstract_es = False
            continue

        if next_is_abstract_en and "abstract_en" not in data:
            data["abstract_en"] = text
            next_is_abstract_en = False
            continue

        lower_text = text.lower()
        if lower_text.startswith(("resumen", "resumo")):
            next_is_abstract_es = True
        elif lower_text.startswith("abstract"):
            next_is_abstract_en = True

    return data


def extract_bibliographic_data(pdf_path: str) -> Dict[str, str]:
    doc = extract_text_lines(pdf_path)

    data = {}

    data.update(extract_title(doc))
    data.update(extract_keywords(doc))
    data.update(extract_metadata(doc))
    data.update(extract_abstracts(doc))

    return data
