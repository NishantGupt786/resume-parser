from flask import Flask, request, redirect, render_template, send_file, after_this_request
from werkzeug.utils import secure_filename
from llmsherpa.readers import LayoutPDFReader
import textract
import os
import re
from spire.doc import Document
from pdfminer.high_level import extract_text

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'docx', 'rtf'}
llmsherpa_api_url = "https://readers.llmsherpa.com/api/document/developer/parseDocument?renderFormat=all"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

STRIP_WHITE = re.compile(r'\s+')
STRIP_EOL = re.compile(r'[\r\n]+')

def extract_text_from_docx_spire(filepath):
    document = Document()
    document.LoadFromFile(filepath)
    text = document.GetText()
    document.Close()
    return text

def extract_text_with_textract(filepath):
    try:
        text = textract.process(filepath).decode('utf-8')
        return text
    except Exception as e:
        return f"An error occurred while extracting text: {str(e)}"

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        tool = request.form.get('tool', 'textract')
        if 'files' not in request.files:
            return redirect(request.url)
        files = request.files.getlist('files')
        if not files:
            return redirect(request.url)

        concatenated_text = ""
        separator = "\n\n--- End of Document ---\n\n"

        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                try:
                    file_extension = filename.rsplit('.', 1)[1].lower()
                    if tool == 'llmsherpa' and file_extension == 'pdf':
                        pdf_reader = LayoutPDFReader(llmsherpa_api_url)
                        doc = pdf_reader.read_pdf(filepath)
                        text = doc.to_text()
                    elif tool == 'spire':
                        if file_extension == 'docx':
                            text = extract_text_from_docx_spire(filepath)
                    elif tool == 'pdfminer':
                        text = extract_text(filepath)
                    else:
                        text = extract_text_with_textract(filepath)
                except Exception as e:
                    text = f"An error occurred while extracting text from {filename}: {str(e)}"
                concatenated_text += text + separator
                os.remove(filepath)

        output_filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'concatenated_text.txt')
        with open(output_filepath, 'w', encoding='utf-8') as f:
            f.write(concatenated_text)

        @after_this_request
        def remove_file(response):
            try:
                os.remove(output_filepath)
            except Exception as e:
                app.logger.error("Error removing or closing downloaded file handle", e)
            return response

        return send_file(output_filepath, as_attachment=True, download_name='concatenated_text.txt')

    return render_template('upload.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
