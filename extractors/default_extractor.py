import pymupdf
from pymupdf4llm import to_markdown
import re
from typing import List, Dict, Optional

SPANISH_KEYWORDS = ["palabras clave", "palavras-chave"]
ENGLISH_KEYWORDS = ["keywords", "key words", "keyword", "key-words"]
ABSTRACT_STOPPERS = SPANISH_KEYWORDS + ENGLISH_KEYWORDS + ["nº"]
ABSTRACTS = ["resumen", "abstract", "resumo"]
NON_NAME_WORDS = ['universidad', 'institución', 'argentina', 'institute', 'nacional', 'departamento', 'buenos aires', 'ciudad', 'méxico', 'entrevista']


def extract_text_lines(pdf_path: str, return_doc: bool = False) -> List[str] | tuple[List[str], pymupdf.Document, str]:
    doc = pymupdf.open(pdf_path)
    markdown = to_markdown(doc)
    full_text = "\n".join(page.get_text() for page in doc)
    lines = [l.strip() for l in full_text.splitlines() if l.strip()]
    return (lines, doc, markdown) if return_doc else lines


def extract_title(markdown: str) -> Dict[str, str]:
    headings = re.findall(r'^(#+)\s+(.*)', markdown, re.MULTILINE)

    if not headings:
        return {}

    heading_levels = {}
    for level, heading in headings:
        level_len = len(level)
        heading_levels.setdefault(level_len, []).append(heading.strip())

    if len(heading_levels) >= 3 and 2 in heading_levels:
        titles = heading_levels[2]
    else:
        titles = heading_levels.get(1, [])

    return {"title": titles[0]} if titles else {}

def extract_keywords(lines: List[str]) -> Dict[str, str]:
    result = {}
    for i, line in enumerate(lines):
        line_lower = line.lower()
        if not result.get("keywords_es") and any(k in line_lower for k in SPANISH_KEYWORDS):
            if i + 1 < len(lines):
                result["keywords_es"] = lines[i + 1].strip().replace(';', ',')
        elif not result.get("keywords_en") and any(k in line_lower for k in ENGLISH_KEYWORDS):
            if i + 1 < len(lines):
                result["keywords_en"] = lines[i + 1].strip().replace(';', ',')
    return result

def extract_metadata(first_two_pages: List[str]) -> Dict[str, str]:
    data = {}
    for line in first_two_pages:
        line = line.strip()
        if "issn" not in data:
            if (m := re.search(r'(?i)ISSN[:\s]*([\d]{4}-[\d]{4})', line)):
                data["issn"] = m.group(1)
        if "publication" not in data or "volume" not in data or "publishing_date" not in data:
            if (m := re.search(r'(.+)\s+nº\s*(\d+)\s*\((.*\d{4})\)', line)):
                data["publication"] = m.group(1).strip()
                data["volume"] = m.group(2).strip()
                data["publishing_date"] = m.group(3).strip()
        if "pages" not in data:
            if (m := re.search(r'pp\.\s*(\d+)-(\d+)', line)):
                data["pages"] = f"{m.group(1)}-{m.group(2)}"

        for line in first_two_pages[:10]:
            if re.search(r'\bRESEÑAS?\b', line, re.IGNORECASE):
                data["tags"] = "RezensionsTagPica"
                break
    
    return data

def extract_abstracts(first_two_pages: List[str], publication: Optional[str] = None) -> Dict[str, str]:
    data = {}
    abstract_lines_es = []
    abstract_lines_en = []
    collecting_es = collecting_en = False

    stop_words = ABSTRACT_STOPPERS[:]
    if publication:
        stop_words.append(publication.lower())

    for line in first_two_pages:
        lower_line = line.lower()
        if not data.get("abstract_es"):
            if "resumen" in lower_line or "resumo" in lower_line:
                collecting_es = True
                continue
            if collecting_es:
                if any(stop in lower_line for stop in stop_words):
                    collecting_es = False
                    continue
                abstract_lines_es.append(line)
        if not data.get("abstract_en"):
            if "abstract" in lower_line and "resumen" not in lower_line:
                collecting_en = True
                continue
            if collecting_en:
                if any(stop in lower_line for stop in stop_words):
                    collecting_en = False
                    continue
                abstract_lines_en.append(line)

    if abstract_lines_es:
        data["abstract_es"] = " ".join(abstract_lines_es).strip()
    if abstract_lines_en:
        data["abstract_en"] = " ".join(abstract_lines_en).strip()

    return data


def extract_bibliographic_data(pdf_path: str) -> Dict[str, str]:
    lines, doc, markdown = extract_text_lines(pdf_path, return_doc=True)

    page1_lines = doc[0].get_text().splitlines()
    page2_lines = doc[1].get_text().splitlines() if len(doc) > 1 else []
    first_two_pages = page1_lines + page2_lines

    data = {}

    data.update(extract_title(markdown))
    data.update(extract_keywords(lines))
    data.update(extract_metadata(first_two_pages))
    data.update(extract_abstracts(first_two_pages, data.get("publication")))

    return data
