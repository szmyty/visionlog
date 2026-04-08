FROM python:3.10-slim

RUN apt-get update && apt-get install --yes \
    curl \
    git \
    build-essential \
    && rm --recursive --force /var/lib/apt/lists/*

RUN curl -sSL https://install.python-poetry.org | python3 - \
    && ln -s /root/.local/bin/poetry /usr/local/bin/poetry

WORKDIR /workspace
