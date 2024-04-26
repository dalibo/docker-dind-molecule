FROM docker:24.0.8-dind

RUN apk add --no-cache python3 python3-dev py3-pip gcc \
	git curl build-base autoconf automake py3-cryptography rsync \
	linux-headers musl-dev libffi-dev openssl-dev openssh

RUN python3 -m venv --upgrade-deps /opt/venv

COPY requirements.txt /opt
COPY ansible_collection_helper.py /opt/
COPY templates /opt/templates/

RUN /opt/venv/bin/pip install -r /opt/requirements.txt
