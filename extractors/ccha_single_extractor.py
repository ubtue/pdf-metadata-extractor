import sys
import fitz  # PyMuPDF
import os
import re
from typing import Dict, Optional, List

def normalize_author_lastname(author: str) -> str:
    return ' '.join(word.title() for word in re.split(r'\s+', author.strip(' ,.')))

def extract_bibliography(page_text: str) -> Dict[str, Optional[str]]:
    data = {'year': None, 'volume': None, 'pages': None, 'title': None, 'authors': []}

    raw_lines = page_text.split('\n')

    bib_index = -1
    for i, line in enumerate(raw_lines[:12]):
        line_stripped = line.strip()
        if re.search(r'\(\d{4}\)', line_stripped) and re.search(r'\d', line_stripped):
            bib_line = line_stripped
            bib_index = i

            year_match = re.search(r'\((\d{4})\)', bib_line)
            if year_match: data['year'] = year_match.group(1)
            vol_match = re.search(r'(\d+)(?=\s*\(\d{4}\))', bib_line)
            if vol_match: data['volume'] = vol_match.group(1)
            page_match = re.search(r'(\d+(?:-\d+))', bib_line)
            if page_match: data['pages'] = page_match.group(1)
            break

    if bib_index == -1:
        return data

    title_parts = []
    i = bib_index + 1

    while i < len(raw_lines):
        line = raw_lines[i].strip()
        if (not line and title_parts) or re.search(r'^\s*by\s+', line, re.IGNORECASE) or re.search(r'^([A-Z][a-z]+\s|[A-Z]\.\s?)+[A-Z]{2,}$', line):
            break
        if line and len(line) > 1:
            title_parts.append(line)
        i += 1

    if title_parts:
        data['title'] = ' '.join(title_parts)

    author_start = max(bib_index + 2, i - 1)

    by_author = None
    for j in range(author_start, min(author_start + 5, len(raw_lines))):
        line = raw_lines[j].strip()
        if re.match(r'^\s*by\s+', line, re.IGNORECASE):
            by_match = re.search(r'by\s+(.+?)(?:\n|$|St\.)', line, re.IGNORECASE)
            if by_match:
                by_author = by_match.group(1).strip()
                break

    if by_author:
        data['authors'].append(normalize_author_lastname(by_author))
    else:
        for j in range(author_start, min(author_start + 5, len(raw_lines))):
            line = raw_lines[j].strip()
            if line and re.match(r'^[A-Z][A-Za-z\s\-\.\'\’]+$', line) and len(line.split()) <= 4:
                data['authors'].append(normalize_author_lastname(line))
                break

    return data

def extract_pdf_bibliography(pdf_path: str) -> Dict[str, Optional[str]]:
    doc = fitz.open(pdf_path)
    try:
        page = doc[0]
        return extract_bibliography(page.get_text())
    finally:
        doc.close()

def extract_pdf_bibliography(pdf_path: str) -> Dict[str, Optional[str]]:
    doc = fitz.open(pdf_path)
    try:
        page = doc[0]
        return extract_bibliography(page.get_text())
    finally:
        doc.close()

def extract_bibliographic_data(pdf_path: str) -> dict:
    entry = extract_pdf_bibliography(pdf_path)
    data = {
            "title" : entry['title'],
            "authors" : entry['authors'] or 'N/A',
            "volume" : entry.get('volume', 'N/A'),
            "year" : entry.get('year', 'N/A'),
            "page" : entry['pages']
    }

    return data
