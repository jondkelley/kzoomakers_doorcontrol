FROM python:3.9-alpine

MAINTAINER Jonathan Kelley <jonk@omg.lol>

ENV DEBIAN_FRONTEND noninteractive

#ADD requirements.txt /
#RUN pip install -r /requirements.txt
ADD . /app/

WORKDIR /app

RUN python3 setup.py install

RUN addgroup -g 15000 -S doorctl && adduser -u 15000 -S doorctl -G doorctl
USER doorctl

EXPOSE 5001
ENTRYPOINT ["doorcontrol"]
