FROM alpine
LABEL org.opencontainers.image.source=https://github.com/ScilifelabDataCentre/dds_cli
RUN apk add python3
RUN adduser -D load-tester
WORKDIR /home/load-tester
COPY upload.sh .
COPY upload upload
RUN chown -R load-tester:load-tester upload.sh upload
USER load-tester
RUN python3 -m venv $HOME/.dds
RUN $HOME/.dds/bin/pip3 install dds-cli
