FROM python:3.7-slim

WORKDIR /app

COPY Pipfile ./
COPY Pipfile.lock ./

RUN apt-get update && apt-get install libsndfile1 ffmpeg -y && \
    pip install pipenv==2018.11.26 && \
    pipenv install --deploy --system && \
    pip uninstall pipenv -y

COPY entrypoint.sh ./
COPY app.py ./

CMD ["./entrypoint.sh"]