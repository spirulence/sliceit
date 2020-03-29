import os
import tempfile
import zipfile

import librosa
import soundfile
import youtube_dl


def beatslice(url):
    yield "DOWNLOADING", None

    data, samplerate = _download_with_youtube_dl(url)

    yield "FINDING_BEATS", None

    transients = _get_transients(data, samplerate)

    yield "CREATING_ZIP_FILE", None

    archive = _put_transients_into_zip(data, samplerate, transients)

    yield "COMPLETE", archive


def _get_transients(data, samplerate):
    transient_frames = librosa.onset.onset_detect(data, sr=samplerate, backtrack=True)
    # noinspection PyTypeChecker
    transient_samples = [0] + librosa.frames_to_samples(transient_frames).tolist()

    return transient_samples


def _put_transients_into_zip(data, samplerate, transients):
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


def _download_with_youtube_dl(url):
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
