from flask import Flask, request, Response, jsonify
from flask_cors import CORS
import tempfile
import os
import requests
import importlib

server = Flask(__name__)
CORS(server, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

@server.route('/', methods=['POST'])
def extract_pdf_metadata():
    url = request.form.get('url')
    site = request.form.get('site', 'default').lower()
    if url:
        response = requests.get(url)
        response.raise_for_status()

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
            tmp_pdf.write(response.content)
            tmp_pdf_path = tmp_pdf.name

        extractor_module_name = f"extractors.{site}_extractor"
        extractor_module = importlib.import_module(extractor_module_name)
        data = extractor_module.extract_bibliographic_data(tmp_pdf_path)

        os.remove(tmp_pdf_path)

        return jsonify(data)
    
    else:
        return Response('Error: url parameter not found.',
                        status=500)


if __name__ == '__main__':
    server.run(host='0.0.0.0', port=8070, debug=True)
