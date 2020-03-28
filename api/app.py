import tempfile
import zipfile
import os
import hashlib
import librosa
import soundfile
import youtube_dl
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from flask import Flask, make_response, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)


projectId = 'beatsliceit'
cred = credentials.ApplicationDefault()
firebase_admin.initialize_app(cred, {
    'projectId': projectId,
})

db = firestore.client()


@app.route("/ping")
def ping():
    return "pong"


def get_transients(data, samplerate):
    transient_frames = librosa.onset.onset_detect(data, sr=samplerate, backtrack=True)
    # noinspection PyTypeChecker
    transient_samples = [0] + librosa.frames_to_samples(transient_frames).tolist()

    return transient_samples


def put_transients_into_zip(data, samplerate, transients):
    with tempfile.TemporaryFile() as temp_file:
        zip = zipfile.ZipFile(temp_file, mode="w")

        for i, start in enumerate(transients[:-1]):
            end = transients[i + 1]
            with tempfile.NamedTemporaryFile(suffix=".wav") as slice_file:
                soundfile.write(slice_file.name, data[start:end], samplerate=samplerate)
                zip.write(slice_file.name, arcname="slice_{}.wav".format(str(i).zfill(5)))

        zip.close()

        temp_file.seek(0)

        return temp_file.read()


def download_with_youtube_dl(url):
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '256',
        }],
        'outtmpl': 'ytdl.mp3'
    }

    current_directory = os.getcwd()

    with tempfile.TemporaryDirectory() as tempdir:

        os.chdir(tempdir)

        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        data, samplerate = librosa.load("./ytdl.mp3")

    os.chdir(current_directory)

    return data, samplerate


@app.route("/slice/<pointer>", methods=["POST"])
def slice_from_pointer(pointer):
    slicing_status = db.collection(u'slicing-status')
    document = slicing_status.document(pointer)
    url = document.get().to_dict()["url"]

    document.update({"status": "DOWNLOADING"})
    data, samplerate = download_with_youtube_dl(url)

    document.update({"status": "FINDING_BEATS"})
    transients = get_transients(data, samplerate)

    document.update({"status": "CREATING_ZIP_FILE"})
    response = make_response(put_transients_into_zip(data, samplerate, transients))

    response.headers['Content-Type'] = 'application/zip'
    response.headers['Content-Disposition'] = 'attachment; filename=sliced.zip'

    document.update({"status": "COMPLETE"})
    return response


@app.route("/slice/prep", methods=["POST"])
def slice_prep():
    url = request.json['url']
    url_hash = hashlib.sha256(bytes(url, 'utf-8')).hexdigest()
    document_dict = {
        'url': url,
        'url_hash': url_hash,
        'status': 'INITIALIZED'
    }

    slicing_status = db.collection(u'slicing-status')
    slicing_status.document(url_hash).set(document_dict)

    return {
        "reference": url_hash
    }


@app.route("/slice/status/<pointer>")
def slice_status(pointer):
    slicing_status = db.collection(u'slicing-status')
    status = slicing_status.document(pointer).get().to_dict()
    return {
        "status": status["status"]
    }
