FROM ubuntu:20.04 as base

### Stage 1 - add/remove packages ###
COPY ./requirements.txt /scripts/

RUN apt update && \
    apt install -yqq \
      python3 \
      python3-pip && \
    pip3 install -r /scripts/requirements.txt && pip3 install --upgrade pyinstaller


### Stage 2 --- collapse layers ###

# FROM scratch
# COPY --from=base / .

# CMD ["/bin/bash"]