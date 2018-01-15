FROM python:2-alpine
EXPOSE 80
WORKDIR /opt/app
COPY ./requirements.txt /opt/app/
RUN pip install -r requirements.txt
ADD . /opt/app
ENV FLASK_APP app.py

#1-enabled, 0-disabled
ENV FLASK_DEBUG 1
CMD flask run --host=0.0.0.0 --port=80