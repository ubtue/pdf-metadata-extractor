import fitz  # PyMuPDF
import re


KEYWORDS_START = ["keywords", "key words", "keyword", "key-words"]
NAME_PATTERN = re.compile(r"^[A-Z][\w'’.-]+(?:\s+[A-Z][\w'’.-]+){1,5}$", re.UNICODE)
ORCID_PATTERN = re.compile(
    r'ORCID\s*:\s*(?:https?:\/\/orcid\.org\/)?'
    r'(\d{4}-\d{4}-\d{4}-\d{3}[\dX])',
    re.IGNORECASE
)

def looks_like_name(s):
    s = s.strip()

    if not NAME_PATTERN.match(s):
        return False

    banned = {
        "Book Review",
        "Abstract",
        "Keywords",
        "Independent Scholar",
    }

    return s not in banned

def pdf_to_markdown(pdf_path: str) -> str:
    doc = fitz.open(pdf_path)
    markdown = ""
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        text = page.get_text("text")
        markdown += f"# Page {page_num + 1}\n\n{text}\n\n---\n\n"
    return markdown

def detect_pdf_page_range(pdf_path):
    doc = fitz.open(pdf_path)
    pdf_length = doc.page_count
    last_page = doc[-1]
    text = last_page.get_text("text")
    lines = [line.strip() for line in text.splitlines()]
    page_numbers = set()
    page_num_pattern = re.compile(r'\b(\d{1,3})\b')

    for line in lines:
        if not line:
            continue
        if len(line) > 60:
            continue
        match = page_num_pattern.search(line)
        if not match:
            continue
        num = int(match.group(1))
        if not (1 <= num <= 2000):
            continue
        if line.startswith(str(num)) or line.endswith(str(num)):
            page_numbers.add(num)
    if not page_numbers:
        return ""
    last_printed_page = max(page_numbers)
    start_page = last_printed_page - pdf_length + 1
    return f"{start_page}-{last_printed_page}"

def clean_text(text: str) -> str:
    text = re.sub(r'(\w)-\s*\n\s*(\w)', r'\1\2', text)
    text = text.replace("\n", " ")
    text = re.sub(r'\s{2,}', ' ', text)
    text = re.sub(r'\s+([.,;:!?])', r'\1', text)
    return text.strip()


def extract_abstract(lines):
    abstract_lines = []
    in_abstract = False
    skip_until_page_number = False
    for line in lines:
        lower = line.lower().strip()
        if lower.startswith("abstract"):
            in_abstract = True
            continue
        if not in_abstract:
            continue
        if lower.startswith(("keywords", "key words", "keyword")):
            break
        if lower.startswith("# page"):
            skip_until_page_number = True
            continue
        if skip_until_page_number:
            if re.fullmatch(r"\d{1,4}", line.strip()):
                skip_until_page_number = False
            continue
        if re.fullmatch(r"\d{1,4}", line.strip()):
            continue
        if line.strip().startswith('---'):
            continue

        abstract_lines.append(line)

    return clean_text(" ".join(abstract_lines))


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

def extract_authors_and_orcids(pdf_path):
    doc = fitz.open(pdf_path)
    page = doc[0]

    blocks = sorted(
        page.get_text("blocks"),
        key=lambda b: (b[1], b[0])
    )

    authors = []
    orcids = []

    for block in blocks:
        x0, y0, x1, y1, text = block[:5]

        lines = [
            line.strip()
            for line in text.splitlines()
            if line.strip()
        ]

        for idx, line in enumerate(lines):
            if looks_like_name(line):
                authors.append({
                    "name": line,
                    "y": y0 + idx,
                    "orcid": ""
                })
            match = ORCID_PATTERN.search(line)
            if match:
                orcids.append({
                    "orcid": match.group(1),
                    "y": y0 + idx
                })

    for oid in orcids:
        candidates = [
            a for a in authors
            if a["y"] <= oid["y"]
        ]
        if not candidates:
            continue
        closest_author = max(
            candidates,
            key=lambda a: a["y"]
        )
        closest_author["orcid"] = oid["orcid"]
    return authors

def extract_bibliographic_data(pdf_path: str) -> dict:
    markdown_text = pdf_to_markdown(pdf_path)
    lines = [line.rstrip() for line in markdown_text.splitlines()]

    pages = detect_pdf_page_range(pdf_path)
    abstract_en = extract_abstract(lines)
    keywords_en = extract_keywords(lines, KEYWORDS_START)

    authors = extract_authors_and_orcids(pdf_path)

    data = {
        "abstract": abstract_en,
        "keywords": keywords_en,
        "pages": pages,
        "author": authors
    }

    return data
