FROM python:3.10-slim

RUN apt-get update && apt-get install --yes \
    curl \
    git \
    build-essential \
    && rm --recursive --force /var/lib/apt/lists/*

RUN pip install --no-cache-dir poetry

WORKDIR /workspace
