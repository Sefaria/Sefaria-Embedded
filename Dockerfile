FROM python:2-alpine

COPY . /usr/src/app/
WORKDIR /usr/src/app/

RUN apk --update add libxml2-dev libxslt-dev libffi-dev gcc musl-dev libgcc openssl-dev curl
RUN apk add jpeg-dev zlib-dev freetype-dev lcms2-dev openjpeg-dev tiff-dev tk-dev tcl-dev

RUN pip install -r requirements.txt

EXPOSE 5000
ENTRYPOINT ["/usr/local/bin/gunicorn"]

CMD ["-w","1","-b","0.0.0.0:5000","--threads","1","app:app","--access-logfile","/dev/stdout","--error-logfile","/dev/stdout"]
