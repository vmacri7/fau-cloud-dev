import os
import io
import json
from flask import Flask, redirect, request, send_file, url_for
import google.generativeai as genai
from google.cloud import storage

storage_client = storage.Client()

BUCKET_NAME = "cloud-native-dev-p1"

# gemini api configuration
genai.configure(api_key=os.environ['GEMINI_API'])

# create upload directory if it doesn't exist
os.makedirs('uploads', exist_ok=True)

app = Flask(__name__)

# initialize gemini
def initialize_gemini_model():
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
    )
    return model

def strip_json_padding(string):
    string = string.replace("```json", "")
    string = string.replace("```", "")
    return string

# analyze image with gemini ai
def analyze_image_with_gemini(image_path):
    model = initialize_gemini_model()
    
    # upload the file to gemini
    file = genai.upload_file(image_path, mime_type="image/jpeg")
    
    # prompt gemini to analyze the image
    prompt = "describe the image. provide a short title and a detailed description. return your response in json format with 'title' and 'description' fields."
    
    # get response from gemini
    response = model.generate_content([file, "\n\n", prompt])

    # strip '''json ... ''' which gemini adds to the response
    json_text = strip_json_padding(response.text)

    # extract json data
    try:
        # attempt to parse json directly from response text
        result = json.loads(json_text)
    except json.JSONDecodeError:
        # if direct parsing fails, populate with default values
        result = {
            "title": "error encountered in generating title",
            "description": "error encountered in generating description"
        }
    
    return result

# list file names in the bucket
def list_cloud_files(bucket_name=BUCKET_NAME):
    bucket = storage_client.bucket(bucket_name)
    blobs = bucket.list_blobs()
    files = []
    for blob in blobs:
        files.append(blob.name)
    return files
    
# uploads file to bucket in the cloud
def upload_file_to_cloud(file, bucket_name=BUCKET_NAME):
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(os.path.basename(file))
    
    # set appropriate content type for images
    content_type = "image/jpeg"
    blob.content_type = content_type
    
    # upload the file
    blob.upload_from_filename(file)
    
    return blob.name

# upload json metadata to cloud storage
def upload_json_to_cloud(json_data, filename, bucket_name=BUCKET_NAME):
    bucket = storage_client.bucket(bucket_name)
    json_filename = os.path.splitext(filename)[0] + ".json"
    blob = bucket.blob(json_filename)
    
    blob.upload_from_string(
        json.dumps(json_data),
        content_type="application/json"
    )
    
    return json_filename

@app.route('/')
def index():
    index_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>image upload app</title>
        <style>
            body { font-family: arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
            .image-list { list-style-type: none; padding: 0; }
            .image-list li { margin-bottom: 10px; }
        </style>
    </head>
    <body>
        <h1>image upload app</h1>
        <form method="post" enctype="multipart/form-data" action="/upload">
          <div>
            <label for="file">choose file to upload</label>
            <input type="file" id="file" name="form_file" accept="image/jpeg"/>
          </div>
          <div>
            <button type="submit">upload image</button>
          </div>
        </form>
        <h2>uploaded images:</h2>
        <ul class="image-list">
    """
    
    file_names = list_files()
    
    for file in file_names:
        # create proxy urls through app instead of direct bucket urls
        file_url = url_for('serve_file', filename=file)
        index_html += f'<li><a href="{file_url}" target="_blank">{file}</a></li>'
    
    index_html += """
        </ul>
    </body>
    </html>
    """
    
    return index_html

@app.route('/upload', methods=["POST"])
def upload():
    file = request.files['form_file']
    
    if file and (file.filename.lower().endswith('.jpg') or file.filename.lower().endswith('.jpeg')):
        # save file temporarily
        temp_path = os.path.join("./uploads", file.filename)
        file.save(temp_path)

        # analyze image using gemini
        image_data = analyze_image_with_gemini(temp_path)
        
        # upload image to cloud
        upload_file_to_cloud(temp_path)

        # upload json metadata to cloud
        upload_json_to_cloud(image_data, file.filename)
        
        # clean up temporary file
        os.remove(temp_path)

    return redirect(url_for('index'))

@app.route('/files')
def list_files():
    files = list_cloud_files()
    jpegs = []
    for file in files:
        if file.lower().endswith(".jpeg") or file.lower().endswith(".jpg"):
            jpegs.append(file)
    
    return jpegs

@app.route('/file/<filename>')
def serve_file(filename):
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(filename)
    
    # create a file-like object from the blob
    file_bytes = blob.download_as_bytes()
    byte_stream = io.BytesIO(file_bytes)
    
    content_type = 'image/jpeg'
    
    # serve the file
    return send_file(
        byte_stream,
        mimetype=content_type,
        as_attachment=False,
        download_name=filename
    )

if __name__ == '__main__':
    app.run(debug=True)