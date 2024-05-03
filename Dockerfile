FROM docker:24.0.8-dind

RUN apk add --no-cache python3 python3-dev py3-pip gcc jq \
	git curl build-base autoconf automake py3-cryptography rsync \
	linux-headers musl-dev libffi-dev openssl-dev openssh-client

RUN python3 -m venv --upgrade-deps /opt/venv

COPY . /usr/local/src/ansible_collection_helper
RUN /opt/venv/bin/pip install --no-cache-dir /usr/local/src/ansible_collection_helper &&\
	rm -rf /usr/local/src/ansible_collection_helper
