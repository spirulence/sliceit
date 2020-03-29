import os
import tempfile
import zipfile
from collections import namedtuple

import librosa
import soundfile
import youtube_dl


SlicingOptions = namedtuple("SlicingOptions", ["sensitivity"])


def beatslice(url, options):
    yield "DOWNLOADING", None

    data, samplerate = _download_with_youtube_dl(url)

    yield "FINDING_BEATS", None

    transients = _get_transients(data, samplerate, options)

    yield "CREATING_ZIP_FILE", None

    archive = _put_transients_into_zip(data, samplerate, transients)

    yield "COMPLETE", archive


def _sensitivity_to_peak_pick_args(sensitivity, samplerate):
    if sensitivity == "HIGH":
        return {
            "pre_max": 0.01 * samplerate // 512,
            "post_max": 1,
            "pre_avg": 0.02 * samplerate // 512,
            "post_avg": 0.02 * samplerate // 512 + 1,
            "delta": 0.02,
            "wait": 0.01 * samplerate // 512
        }
    if sensitivity == "LOW":
        return {
            "pre_max": 0.20 * samplerate // 512,
            "post_max": 1,
            "pre_avg": 0.6 * samplerate // 512,
            "post_avg": 0.6 * samplerate // 512 + 1,
            "delta": 0.2,
            "wait": 0.12 * samplerate // 512
        }


def _get_transients(data, samplerate, options):
    if options.sensitivity == "MEDIUM":
        transient_frames = librosa.onset.onset_detect(data, sr=samplerate, backtrack=True)
    else:
        peak_args = _sensitivity_to_peak_pick_args(options.sensitivity, samplerate)
        transient_frames = librosa.onset.onset_detect(data, sr=samplerate, backtrack=True, **peak_args)

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
