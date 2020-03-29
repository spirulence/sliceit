import hashlib
import datetime
import secrets

import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from flask import Flask, make_response, request
from flask_cors import CORS

from beatslice.slice import beatslice, SlicingOptions

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


@app.route("/slice/<pointer>", methods=["POST"])
def slice_from_pointer(pointer):
    slicing_status = db.collection(u'slicing-status')
    document = slicing_status.document(pointer)
    stored_data = document.get().to_dict()

    url = stored_data["url"]

    options = SlicingOptions(sensitivity=stored_data["slicing_options"].get("sensitivity", "MEDIUM"))

    final_archive = None

    for status, archive in beatslice(url, options):
        document.update({"status": status})
        final_archive = archive

    if final_archive:
        response = make_response(final_archive)

        response.headers['Content-Type'] = 'application/zip'
        response.headers['Content-Disposition'] = 'attachment; filename=sliced.zip'

        document.update({'completed_at': datetime.datetime.utcnow().isoformat()})

        return response


@app.route("/slice/prep", methods=["POST"])
def slice_prep():
    url = request.json['url']
    sensitivity = request.json['sensitivity']
    assert sensitivity in ('HIGH', 'MEDIUM', 'LOW')

    time = datetime.datetime.utcnow().isoformat()
    random_bytes = secrets.token_bytes(16)

    identifier = bytes(url, 'utf-8') + bytes(time, 'utf-8') + random_bytes

    reference = hashlib.sha256(identifier).hexdigest()

    document_dict = {
        'url': url,
        'initialized_at': time,
        'slicing_options': {
            'sensitivity': sensitivity
        },
        'status': 'INITIALIZED'
    }

    slicing_status = db.collection(u'slicing-status')
    slicing_status.document(reference).set(document_dict)

    return {
        "reference": reference
    }


@app.route("/slice/status/<pointer>")
def slice_status(pointer):
    slicing_status = db.collection(u'slicing-status')
    status = slicing_status.document(pointer).get().to_dict()
    return {
        "status": status["status"]
    }
