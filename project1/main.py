import os
import shutil
from flask import Flask, redirect, request, send_file

from google.cloud import storage

storage_client = storage.Client()

BUCKET_NAME = "cloud-native-dev-p1"

os.makedirs('files', exist_ok = True)

app = Flask(__name__)

# list file names in the bucket
def list_cloud_files(bucket_name = BUCKET_NAME):
    bucket = storage_client.bucket(bucket_name)
    blobs = bucket.list_blobs()
    files = []
    for blob in blobs:
        files.append(blob.name)
    return files
    
# uploads file to bucket in the cloud
def upload_file_to_cloud(file, bucket_name = BUCKET_NAME):
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(os.path.basename(file))
    blob.upload_from_filename(file)

def download_file_from_cloud(file, local_path, bucket_name = BUCKET_NAME):
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(file)
    blob.download_to_filename(local_path)



@app.route('/')
def index():
    index_html="""
<form method="post" enctype="multipart/form-data" action="/upload" method="post">
  <div>
    <label for="file">Choose file to upload</label>
    <input type="file" id="file" name="form_file" accept="image/jpeg"/>
  </div>
  <div>
    <button>Submit</button>
  </div>
</form>"""    
    files = list_files()
    for file in files:
        index_html += "<li><a href=\"/files/" + file + "\">" + file + "</a></li>"

    return index_html

@app.route('/upload', methods=["POST"])
def upload():
    file = request.files['form_file']  # item name must match name in HTML form
    file_path = os.path.join("./files", file.filename)
    file.save(file_path)
    upload_file_to_cloud(file_path)

    return redirect("/")

@app.route('/files')
def list_files():
    files = list_cloud_files()
    jpegs = []
    for file in files:
        if file.lower().endswith(".jpeg") or file.lower().endswith(".jpg"):
            jpegs.append(file)
    
    return jpegs

@app.route('/files/<filename>')
def get_file(filename):
    local_path = os.path.join('./files', filename)

    # check if file exists locally
    if not os.path.exists(local_path):
        # temp download location
        temp_download = f"./{filename}"
        download_file_from_cloud(filename, temp_download, BUCKET_NAME)
        shutil.move(temp_download, local_path)  # move after successful download to prevent corruption

    return send_file(local_path)


if __name__ == '__main__':
    # app.run(debug=True)
    app.run()