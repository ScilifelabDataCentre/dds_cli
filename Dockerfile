FROM python:3.7-alpine

WORKDIR /delivery_portal

COPY requirements_cli.txt requirements_cli.txt

RUN pip3 install -r requirements_cli.txt
