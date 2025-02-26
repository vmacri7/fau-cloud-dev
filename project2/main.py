import os
import io
from flask import Flask, redirect, request, send_file, url_for

from google.cloud import storage

storage_client = storage.Client()

BUCKET_NAME = "cloud-native-dev-p1"

# create upload directory if it doesn't exist
os.makedirs('uploads', exist_ok=True)

app = Flask(__name__)

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

@app.route('/')
def index():
    index_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Image Upload App</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
            .image-list { list-style-type: none; padding: 0; }
            .image-list li { margin-bottom: 10px; }
        </style>
    </head>
    <body>
        <h1>Image Upload App</h1>
        <form method="post" enctype="multipart/form-data" action="/upload">
          <div>
            <label for="file">Choose file to upload</label>
            <input type="file" id="file" name="form_file" accept="image/jpeg"/>
          </div>
          <div>
            <button type="submit">Upload Image</button>
          </div>
        </form>
        <h2>Uploaded Images:</h2>
        <ul class="image-list">
    """
    
    file_names = list_files()
    
    for file in file_names:
        # create proxy URLs through app instead of direct bucket URLs
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
        
        # upload to cloud
        upload_file_to_cloud(temp_path)
        
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
    
    # determine content type
    content_type = 'image/jpeg'
    if filename.lower().endswith('.png'):
        content_type = 'image/png'
    
    # serve the file
    return send_file(
        byte_stream,
        mimetype=content_type,
        as_attachment=False,
        download_name=filename
    )

if __name__ == '__main__':
    app.run(debug=True)