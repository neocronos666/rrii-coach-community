# syntax=docker/dockerfile:1.7
FROM python:3.13.14-slim-bookworm

ARG PRE_COMMIT_VERSION=4.6.0

RUN apt-get update \
    && apt-get install --yes --no-install-recommends git \
    && python -m pip install --no-cache-dir "pre-commit==${PRE_COMMIT_VERSION}" \
    && rm -rf /var/lib/apt/lists/*

RUN git config --system --add safe.directory /workspace

RUN groupadd --gid 10001 quality \
    && useradd --uid 10001 --gid quality --create-home quality

ENV PRE_COMMIT_HOME=/home/quality/.cache/pre-commit

WORKDIR /workspace
USER quality

ENTRYPOINT ["pre-commit"]
