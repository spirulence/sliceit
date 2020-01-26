FROM python:3.7-alpine

WORKDIR /app

COPY Pipfile ./
COPY Pipfile.lock ./

RUN pip install pipenv==2018.11.26 && \
    pipenv install --deploy --system && \
    pip uninstall pipenv -y

COPY entrypoint.sh ./
COPY app.py ./

CMD ["./entrypoint.sh"]