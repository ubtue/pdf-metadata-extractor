from flask import Flask, request, Response, jsonify
from flask_cors import CORS
import tempfile
import os
import requests
import importlib
import traceback
from extractors import revista_de_historia_de_las_prisiones_extractor

server = Flask(__name__)
CORS(server, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

@server.route('/', methods=['POST'])
def extract_pdf_metadata():
    url = request.form.get('url')
    site = request.form.get('site', '').lower()

    if not url:
        return jsonify({"error": "url parameter not found"}), 400

    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, verify=False, timeout=15)
        response.raise_for_status()

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
            tmp_pdf.write(response.content)
            tmp_pdf_path = tmp_pdf.name

        extractor_module = revista_de_historia_de_las_prisiones_extractor
        if site:
            try:
                extractor_module = importlib.import_module(f"extractors.{site}_extractor")
                importlib.reload(extractor_module)
            except ModuleNotFoundError:
                pass

        data = extractor_module.extract_bibliographic_data(tmp_pdf_path)

    except Exception as e:
        traceback.print_exc()
        return jsonify({
            "error_type": type(e).__name__,
            "error_msg": str(e)
        }), 500

    finally:
        try:
            os.remove(tmp_pdf_path)
        except Exception:
            pass

    return jsonify(data)


if __name__ == '__main__':
    server.run(host='0.0.0.0', port=8090, debug=True)
