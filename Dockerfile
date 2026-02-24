FROM python:3.12-alpine AS builder

RUN apk add --no-cache python3 python3-dev py3-pip gcc \
	git curl build-base autoconf automake py3-cryptography \
	linux-headers musl-dev libffi-dev openssl-dev

COPY . /usr/local/src/ansible_collection_helper
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /build/wheels /usr/local/src/ansible_collection_helper

FROM docker:28.1.1-dind
RUN apk add --no-cache python3 py3-pip jq py3-cryptography rsync \
    openssh-client git libpq
COPY --from=builder /build/wheels /wheels
COPY --from=ghcr.io/astral-sh/uv:0.10.5 /uv /uvx /bin/
RUN uv venv /opt/venv --python 3.12 && \
    uv pip install --no-cache --python /opt/venv /wheels/*
