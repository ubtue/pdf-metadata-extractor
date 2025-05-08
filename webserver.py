from flask import Flask, request, Response, jsonify
from flask_cors import CORS
import tempfile
import os
import requests
import importlib
from extractors import revista_de_historia_de_las_prisiones_extractor

server = Flask(__name__)
CORS(server, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

@server.route('/', methods=['POST'])
def extract_pdf_metadata():
    url = request.form.get('url')
    site = request.form.get('site', '').lower()
    if url:
        response = requests.get(url)
        response.raise_for_status()

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
            tmp_pdf.write(response.content)
            tmp_pdf_path = tmp_pdf.name

        extractor_module = revista_de_historia_de_las_prisiones_extractor

        if site:
            try:
                extractor_module = importlib.import_module(f"extractors.{site}_extractor")
            except ModuleNotFoundError:
                pass

        data = extractor_module.extract_bibliographic_data(tmp_pdf_path)

        os.remove(tmp_pdf_path)

        return jsonify(data)
    
    else:
        return Response('Error: url parameter not found.',
                        status=500)


if __name__ == '__main__':
    server.run(host='0.0.0.0', port=8090, debug=True)
