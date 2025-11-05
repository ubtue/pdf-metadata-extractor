import fitz  # PyMuPDF
import re
import unicodedata

PUA_MAP = {
    '\uf061': 'α', '\uf062': 'β', '\uf063': 'γ', '\uf064': 'δ', '\uf065': 'ε',
    '\uf066': 'ζ', '\uf067': 'η', '\uf068': 'θ', '\uf069': 'ι', '\uf06a': 'κ',
    '\uf06b': 'λ', '\uf06c': 'μ', '\uf06d': 'ν', '\uf06e': 'ξ', '\uf06f': 'ο',
    '\uf070': 'π', '\uf071': 'ρ', '\uf072': 'σ', '\uf073': 'τ', '\uf074': 'υ',
    '\uf075': 'φ', '\uf076': 'χ', '\uf077': 'ψ', '\uf078': 'ω', '\uf020': ' ',
}

AUTHOR_BIO_PATTERNS = [
    r"\bPhD\b", r"\bDr\b", r"\bProf\b", r"\bcandidate\b", r"\bPostgraduate\b", r"\bTeaching Associate\b",
    r"\bDepartment\b", r"\bUniversity\b", r"\bUnited Kingdom\b", r"\bGermany\b",
    r"\bSweden\b", r"\bNorway\b"
]

KEYWORDS_START = ["keywords", "key words", "keyword", "key-words", "schlagwörter", "stichworte"]

def clean_pua(text: str) -> str:
    for bad, good in PUA_MAP.items():
        text = text.replace(bad, good)
    return unicodedata.normalize("NFC", text)

def pdf_to_markdown(pdf_path: str) -> str:
    doc = fitz.open(pdf_path)
    markdown = ""
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        text = page.get_text("text")
        markdown += f"# Page {page_num + 1}\n\n{text}\n\n---\n\n"
    return clean_pua(markdown)

def detect_pdf_page_range(markdown_text: str) -> str:
    lines = [line.strip() for line in markdown_text.splitlines()]
    pdf_page_numbers = []
    expect_page_number = False

    for line in lines:
        if line.lower().startswith("# page"):
            expect_page_number = True
            continue

        if expect_page_number:
            if line.strip().isdigit():
                num = int(line.strip())
                pdf_page_numbers.append(num)
                expect_page_number = False

    if pdf_page_numbers:
        first, last = min(pdf_page_numbers), max(pdf_page_numbers)
        return f"{first}-{last}" if first != last else str(first)
    return ""

def clean_text(text: str) -> str:
    text = re.sub(r'(\w)-\s*\n\s*(\w)', r'\1\2', text)
    text = text.replace("\n", " ")
    text = re.sub(r'\s{2,}', ' ', text)
    text = re.sub(r'\s+([.,;:!?])', r'\1', text)
    return text.strip()

def remove_author_bio(lines):
    clean_lines = []
    skip_block = False
    for line in lines:
        if any(re.search(pat, line, re.IGNORECASE) for pat in AUTHOR_BIO_PATTERNS):
            skip_block = True
            continue
        if skip_block and not line.strip():
            skip_block = False
            continue
        if not skip_block:
            clean_lines.append(line)
    return clean_lines

def extract_abstract(lines, author_bio_patterns):
    abstract_lines = []
    in_abstract = False
    skip_block = False
    skip_next_nonempty_line = False

    for line in lines:
        lower = line.lower().strip()

        if lower.startswith("abstract") or lower.startswith("zusammenfassung"):
            in_abstract = True
            continue

        if not in_abstract:
            continue

        if lower.startswith("keywords") or lower.startswith("schlagwörter"):
            break
        if re.match(r'^\d+\s+\w', line):
            break

        if any(re.search(pat, line, re.IGNORECASE) for pat in author_bio_patterns):
            skip_block = True
            continue
        if skip_block and not line.strip():
            skip_block = False
            continue
        if skip_block:
            continue

        if lower.startswith("# page"):
            skip_next_nonempty_line = True
            continue

        if skip_next_nonempty_line:
            if line.strip():
                skip_next_nonempty_line = False
                continue
            else:
                continue

        if line.strip().isdigit():
            continue

        if line.strip().startswith('---'):
            continue

        abstract_lines.append(line)

    abstract_text = " ".join(abstract_lines)
    return clean_text(abstract_text)

def extract_keywords(lines, keyword_starts):
    keywords_lines = []
    in_keywords = False

    for line in lines:
        lower = line.lower().strip()

        if any(lower.startswith(k) for k in keyword_starts):
            in_keywords = True
            parts = line.split(None, 1)
            if len(parts) > 1:
                keywords_lines.append(parts[1].strip())
            continue

        if in_keywords:
            if not line.strip() and not keywords_lines:
                continue
            if not line.strip() or line.strip().startswith("---"):
                break
            keywords_lines.append(line.strip())

    keywords_text = " ".join(keywords_lines)
    keywords = [k.strip().rstrip(".") for k in re.split(r"[;,]", keywords_text) if k.strip()]
    return ", ".join(keywords)

def extract_bibliographic_data(pdf_path: str) -> dict:
    markdown_text = pdf_to_markdown(pdf_path)
    lines = [line.rstrip() for line in markdown_text.splitlines()]

    abstract_en = extract_abstract(lines, AUTHOR_BIO_PATTERNS)

    keywords_en = extract_keywords(lines, KEYWORDS_START)

    data = {
        "abstract_en": abstract_en,
        "keywords_en": keywords_en,
        "pages": detect_pdf_page_range(markdown_text)
    }

    return data