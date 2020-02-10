import tempfile
import zipfile
import os
import hashlib
import librosa
import requests
import soundfile
import youtube_dl
from firebase_admin import credentials
from firebase_admin import firestore
from flask import Flask, make_response, request

app = Flask(__name__)


projectId = 'beatsliceit'
cred = credentials.ApplicationDefault()
firebase_admin.initialize_app(cred, {
    'projectId': projectId,
})

@app.route("/ping")
def ping():
    return "pong"


def get_transients(file_name):
    x, sr = librosa.load(file_name)

    transient_frames = librosa.onset.onset_detect(x, sr=sr, backtrack=True)
    # noinspection PyTypeChecker
    transient_samples = [0] + librosa.frames_to_samples(transient_frames).tolist()

    return x, sr, transient_samples


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


def youtube_dl_transients(url):
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

        data, samplerate, transients = get_transients("./ytdl.mp3")

    os.chdir(current_directory)

    return data, samplerate, transients


@app.route("/slice/<path:url>", methods=["GET", "POST"])
def slice(url):
    if "youtube" in url:
        data, samplerate, transients = youtube_dl_transients(url+"?v="+request.args.get("v"))
    else:
        data, samplerate, transients = plain_request_transients(url)

    bytes = put_transients_into_zip(data, samplerate, transients)

    response = make_response(bytes)

    response.headers['Content-Type'] = 'application/zip'
    response.headers['Content-Disposition'] = 'attachment; filename=sliced.zip'

    return response

@app.route("/slice/prep", methods=["POST"])
def slice_prep():
    db = firestore.client()
    url = request.json()['url']
    urlHash = hashlib.sha256(bytes(url, 'utf-8')).hexdigest()
    documentDict = {
        'url': url,
        'url_hash': urlHash,
        'status': 'INITIALIZE'
    }

    slicing_status = db.collection(u'slicing-status')
    slicing_status.document(urlHash).set(documentDict)


def plain_request_transients(url):
    filetype = "." + url.rpartition('.')[2]
    with tempfile.NamedTemporaryFile(suffix=filetype) as f:
        r = requests.get(url)
        f.write(r.content)

        data, samplerate, transients = get_transients(f.name)
    return data, samplerate, transients
