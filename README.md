# PDF-Metadata-Extractor

This project provides a Flask-based web server that downloads PDF files from provided URLs and extracts bibliographic metadata from them. The extraction is done using custom extractor modules tailored for specific sources or journals. The server supports CORS and is containerized using Docker and Docker Compose for deployment.

---

## Features

- Accepts PDF URLs via POST requests.
- Supports dynamic extractor modules based on a `site` parameter.
- Extracts metadata such as title, keywords (in Spanish and English), ISSN, volume, publishing date, pages, abstracts, and tags.
- Uses PDF parsing with `pymupdf`, `pypandoc`, and `panflute` for accurate content extraction.
- Runs in a lightweight Docker container.
- CORS enabled for cross-origin requests.

---

## Project Structure

```plaintext
.
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── webserver.py
└── extractors/
    └── revista_de_historia_de_las_prisiones_extractor.py
```


- **webserver.py**: Main Flask app handling PDF download and metadata extraction.
- **extractors/**: Folder containing extractor modules for different journals/sites.
- **Dockerfile**: Defines the Docker image for the webserver.
- **docker-compose.yml**: Docker Compose config to run the container.
- **requirements.txt**: Python dependencies.

---

## Setup

### 1. Clone the Repository

```bash
git clone git@github.com:ubtue/pdf-metadata-extractor.git
cd pdf-metadata-extractor
```

### 2. Choose a Run Option
#### Option 1: Run with Docker (recommended)

Make sure Docker and Docker Compose are installed.

```bash
docker-compose build
docker-compose up
```

The server will be accessible at: `http://localhost:8090`

#### Option 2: Run locally (for development)

```bash
pip install -r requirements.txt
python webserver.py
```

### Example Usage

```bash
curl -d "url=https://www.revistadeprisiones.com/wp-content/uploads/2024/06/064-067-RHP-18-Enero-Junio-2024.pdf" \
     -d "site=revista_de_historia_de_las_prisiones" \
     http://localhost:8090/ > output.json
```

---

## API
### POST /
**Parameters (form-data):**

* `url` (required): URL of the PDF file to download and extract metadata from.

* `site` (optional): Name of the extractor module to use (corresponding to a Python file in `extractors/`). Defaults to `revista_de_historia_de_las_prisiones_extractor`.

**Response**

* Returns a JSON object containing extracted metadata fields such as:

```json
{
  "title": "Palacio Negro: El final de Lecumberri y el 'Nuevo' penitenciarismo mexicano, 1971–1976",
  "keywords_es": "Palacio Negro de Lecumberri, México, Penitenciarismo, Ley de Normas Mínimas",
  "keywords_en": "Palacio Negro de Lecumberri, Mexico, Penitentiary, Minimum Standards Law",
  "issn": "2451-6473",
  "volume": "18",
  "publishing_date": "Enero-Junio 2024",
  "pages": "64-67",
  "abstract_es": "El libro presenta de forma narrativa y cronológica los últimos días de la Penitenciaría de Lecumberri.",
  "abstract_en": "The book narrates the final days of the Lecumberri Penitentiary and reforms attempted in the 1970s.",
  "tags": "RezensionstagPica"
}
```

**Error**

* Returns HTTP 500 if `url` parameter is missing or if there are issues fetching the PDF.

---

## Extractor Module

Each extractor module in `extractors/` must implement the function:

```python
def extract_bibliographic_data(pdf_path: str) -> dict:
    ...
```

which receives the path to a downloaded PDF file and returns a dictionary with extracted metadata.

The included extractor ([revista_de_historia_de_las_prisiones_extractor.py](./extractors/revista_de_historia_de_las_prisiones_extractor.py)) parses the PDF using:

* `pymupdf` to open and read PDF pages.

* `pymupdf4llm.to_markdown` and `pypandoc` to convert PDF content into a structured format.

* `panflute` to parse and navigate the document content.

* Regular expressions to extract fields like ISSN, volume, pages, keywords, abstracts, and tags.

---

## Dependencies

* Flask

* Flask-CORS

* requests

* pymupdf

* pymupdf4llm

* pypandoc

* panflute

(See [requirements.txt](./requirements.txt) for exact versions)

---

## License

This project is licensed under the [GNU Affero General Public License v3.0](https://www.gnu.org/licenses/agpl-3.0.html).  
See the [LICENSE](./LICENSE) file for details.