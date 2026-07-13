import sys
import fitz  # PyMuPDF
import os
import json
import re
from typing import List, Dict

def extract_volume_year_from_front_page(pdf_path):
    try:
        doc = fitz.open(pdf_path)
        if doc.page_count == 0:
            doc.close()
            return {"volume": "N/A", "year": "N/A"}
            
        front_page = doc[0]
        blocks = front_page.get_text("dict")["blocks"]
        doc.close()
        
        all_spans_text = []
        for block in blocks:
            if block["type"] == 0:
                for line in block["lines"]:
                    for span in line["spans"]:
                        text = span["text"].strip()
                        if text:
                            all_spans_text.append(text)
        
        full_text = " ".join(all_spans_text)
        
        volume_patterns = [
            r'VOLUME\s+(\d+)',
            r'vol\s+(\d+)',
            r'\(vol\s+(\d+)',
        ]
        
        year_patterns = [
            r'^\*\*(\d{4})\*\*', 
            r'^(\d{4})\s',
            r'(\d{4})-\d{2}-\d{2}',
            r'\b(\d{4})\b',         
        ]
        
        volume = "N/A"
        year = "N/A"
        
        for pattern in volume_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                volume = match.group(1)
                break
        
        for pattern in year_patterns:
            match = re.search(pattern, full_text)
            if match:
                year = match.group(1)
                break
        
        return {"volume": volume, "year": year}
        
    except Exception:
        return {"volume": "N/A", "year": "N/A"}

def get_page_lines_with_spans(page):
    try:
        blocks = page.get_text("dict")["blocks"]
        lines_out = []
        for block in blocks:
            if block["type"] != 0:
                continue
            for line in block["lines"]:
                spans = line.get("spans", [])
                if spans:
                    lines_out.append(spans)
        return lines_out
    except Exception:
        return []

def spans_to_text(spans):
    return " ".join(s["text"].strip() for s in spans if s["text"].strip())

def spans_to_italic_text(spans):
    return " ".join(s["text"].strip() for s in spans if s["text"].strip() and (s["flags"] & 2))

def is_page_ref(text):
    return bool(re.match(r'^\d+(-\d+)?$', text.strip()))

def looks_like_author(text):
    if not text or not text.strip():
        return False
    words = [w.strip() for w in text.split() if w.strip()]
    clean_text = text.strip()
    return (1 <= len(words) <= 5 and 
            len(clean_text) > 0 and clean_text[0].isupper() and 
            not is_page_ref(clean_text) and
            len(clean_text) < 30)

def is_section_header(text):
    if not text.strip():
        return False
    text_upper = text.strip().upper()
    section_patterns = [
        r'^(ARTICLES?|REVIEWS?|HISTORICAL\s+NOTES)$',
        r'^\w+\s+(NOTES?|BIBLIOGRAPHY)$',
        r'^ABSTRACTS?/RÉSUMÉS$',
        r'^SUBMISSION\s+GUIDELINES$'
    ]
    return any(re.match(pattern, text_upper) for pattern in section_patterns)

def is_review_pattern(title_texts, author_candidates):
    full_title = " ".join(title_texts).lower()
    return "by " in full_title

def _finalize_entry(current_entry, page_ref):
    authors = " ".join(current_entry["authors"]).strip()
    title_parts = [t.strip() for t in current_entry["title_text"] if t.strip()]
    title = " ".join(title_parts).strip()
    
    if not title and not authors:
        return []
    
    is_review = is_review_pattern(current_entry["title_text"], current_entry["authors"])
    if is_review:
        full_text = " ".join(title_parts + current_entry["authors"])
        match = re.search(r'^(.+?)\s+by\s+(.+)$', full_text, re.I)
        if match:
            title = match.group(1).strip()
            authors = match.group(2).strip()
    
    entry = {
        "title": title.rstrip('.') or authors.rstrip('.'),
        "authors": authors.rstrip('.'),
        "page": page_ref or "N/A",
        "pattern": "review" if is_review else "article"
    }
    return [entry]

def extract_toc_from_page(page):
    lines = get_page_lines_with_spans(page)
    if not lines:
        return []
        
    entries = []
    skip_patterns = ["Table of Contents", "Final.indd", "Hist Studies"]
    
    i = 0
    current_entry = {"title_text": [], "authors": [], "page": None}
    pending_authors = []
    
    while i < len(lines):
        spans = lines[i]
        line_text = spans_to_text(spans).strip()
        
        if (not line_text or 
            any(skip in line_text for skip in skip_patterns) or 
            re.match(r'^\d{4}-\d{2}-\d{2}', line_text)):
            i += 1
            continue
        
        if is_section_header(line_text):
            if current_entry["title_text"] or current_entry["authors"]:
                entries.extend(_finalize_entry(current_entry, current_entry["page"]))
            current_entry = {"title_text": [], "authors": [], "page": None}
            pending_authors = []
            i += 1
            continue
        
        page_match = re.search(r'\b(\d+(?:-\d+)?)\b\s*$', line_text)
        if page_match:
            page_num = page_match.group(1)
            title_part = line_text[:page_match.start()].strip()
            
            if title_part:
                current_entry["title_text"].append(title_part)
            current_entry["page"] = page_num
            
            if current_entry["title_text"] or current_entry["authors"] or pending_authors:
                final_entry = {
                    "title_text": current_entry["title_text"],
                    "authors": current_entry["authors"] + pending_authors,
                    "page": page_num
                }
                entries.extend(_finalize_entry(final_entry, page_num))
            
            current_entry = {"title_text": [], "authors": [], "page": None}
            pending_authors = []
            i += 1
            continue
        
        if is_page_ref(line_text):
            if current_entry["title_text"] or current_entry["authors"] or pending_authors:
                final_entry = {
                    "title_text": current_entry["title_text"],
                    "authors": current_entry["authors"] + pending_authors,
                    "page": line_text
                }
                entries.extend(_finalize_entry(final_entry, line_text))
            current_entry = {"title_text": [], "authors": [], "page": None}
            pending_authors = []
            i += 1
            continue
        
        if looks_like_author(line_text):
            if not current_entry["title_text"]:
                pending_authors.append(line_text)
            else:
                current_entry["authors"].append(line_text)
        else:
            current_entry["title_text"].append(line_text)
        
        i += 1
    
    if current_entry["title_text"] or current_entry["authors"] or pending_authors:
        final_entry = {
            "title_text": current_entry["title_text"],
            "authors": current_entry["authors"] + pending_authors,
            "page": current_entry["page"]
        }
        entries.extend(_finalize_entry(final_entry, current_entry["page"]))
    
    return [e for e in entries if e["title"].strip() and len(e["title"]) > 5 and not is_page_ref(e["title"])]

def extract_toc_entries(pdf_path, toc_page_index=2):
    try:
        volume_year = extract_volume_year_from_front_page(pdf_path)
        doc = fitz.open(pdf_path)
        if doc.page_count == 0:
            return []
            
        for page_idx in [toc_page_index, 1, 0, 3]:
            if page_idx < doc.page_count:
                try:
                    page = doc[page_idx]
                    entries = extract_toc_from_page(page)
                    if entries:
                        for entry in entries:
                            entry["volume"] = volume_year["volume"]
                            entry["year"] = volume_year["year"]
                        doc.close()
                        return entries
                except Exception as e:
                    continue
        
        doc.close()
        return []
    except Exception as e:
        return []

def save_entries_as_json(entries, json_path):
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)

def extract_bibliographic_data(pdf_path: str) -> List[Dict]:
    toc_entries = extract_toc_entries(pdf_path)
    if not toc_entries:
        return []
    data = []
    for entry in toc_entries:
        article = {
                "title" : entry['title'],
                "authors" : entry['authors'] or 'N/A',
                "volume" : entry.get('volume', 'N/A'),
                "year" : entry.get('year', 'N/A'),
                "page" : entry['page'],
                "pattern" : entry['pattern'].upper()
                }
        data.append(article)
    return data
