import fitz
import re
import unicodedata


def pdf_first_page_markdown(pdf_path: str) -> str:
    doc = fitz.open(pdf_path)
    first_page = doc.load_page(0)
    return first_page.get_text("text")


def detect_pdf_page_range(markdown_text: str) -> str:
    markdown_text = unicodedata.normalize("NFC", markdown_text)

    pattern = re.compile(
        r'Hap[aá]g\s*([\dIVXLC]+)\s*,\s*No\.\s*([\d-]+)\s*'
        r'\((\d{4})\)\s*'
        r'(\d+)\s*-\s*(\d+)',
        re.IGNORECASE
    )

    for line in markdown_text.splitlines():
        match = pattern.search(line)
        if match:
            return f"{match.group(4)}-{match.group(5)}"

    return ""


def extract_bibliographic_data(pdf_path: str) -> dict:
    markdown_text = pdf_first_page_markdown(pdf_path)

    data = {
        "pages": detect_pdf_page_range(markdown_text)
    }

    return data
