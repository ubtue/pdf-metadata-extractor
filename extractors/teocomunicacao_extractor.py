import pymupdf
from pymupdf4llm import to_markdown
import pypandoc
import panflute
import io
import re
import fitz
import unicodedata
from typing import Dict

def extract_text_lines(pdf_path: str) -> list[str]:
    doc = fitz.open(pdf_path)
    lines = []
    for page in doc:
        text = page.get_text()
        for line in text.splitlines():
            normalized_line = unicodedata.normalize('NFKC', line).replace('\u00A0', ' ')
            lines.append(normalized_line.strip())
    return lines

def extract_pages(lines: list[str]) -> Dict[str, str]:
    for line in lines:
        line = unicodedata.normalize('NFKC', line).replace('\u00A0', ' ')
        m = re.search(r'(?:v\.\s*\d+,\s*(?:n\.|Nº)\s*\d+,\s*p\.\s*(\d+-\d+)|p\.\s*(\d+-\d+))', line)
        if m:
            page_range = m.group(1) if m.group(1) else m.group(2)
            return {"pages": page_range}
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
    lines = extract_text_lines(pdf_path)

    data = {}
    data.update(extract_pages(lines))

    if "pages" not in data:
        data.update(extract_pages_fallback(pdf_path))

    return data
