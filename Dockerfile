FROM docker:dind

RUN apk add --no-cache python3 python3-dev py3-pip py3-virtualenv gcc \
	git curl build-base autoconf automake py3-cryptography rsync \
	linux-headers musl-dev libffi-dev openssl-dev openssh

RUN python3 -m virtualenv /opt/venv

RUN . /opt/venv/bin/activate && python -m pip install --upgrade pip

COPY dockerfiles/requirements.txt /opt

RUN . /opt/venv/bin/activate && pip3 install -r /opt/requirements.txt
