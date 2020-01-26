import tempfile
import zipfile

import librosa
import requests
import soundfile
from flask import Flask, make_response

app = Flask(__name__)


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

        temp_file.seek(0)

        return temp_file.read()


@app.route("/slice/<path:url>")
def slice(url):
    filetype = "." + url.rpartition('.')[2]

    with tempfile.NamedTemporaryFile(suffix=filetype) as f:
        r = requests.get(url)
        f.write(r.content)

        data, samplerate, transients = get_transients(f.name)

    bytes = put_transients_into_zip(data, samplerate, transients)

    response = make_response(bytes)

    response.headers['Content-Type'] = 'application/zip'
    response.headers['Content-Disposition'] = 'attachment; filename=sliced.zip'

    return response
