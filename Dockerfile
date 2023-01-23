# syntax=docker/dockerfile:1
FROM python:3.8-alpine

WORKDIR /app

COPY src/requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

COPY src/*.py ./

CMD [ "python3", "./Diematic32MQTT.py"]
