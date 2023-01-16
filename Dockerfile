FROM python:3.11-slim-bullseye

COPY . /dbyml
RUN pip install --no-cache-dir /dbyml && \
    rm -rf /root/.cache /dbyml

WORKDIR /work
ENTRYPOINT [ "dbyml" ]
