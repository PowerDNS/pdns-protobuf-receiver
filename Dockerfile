FROM python:3.8-alpine

LABEL name="PDNS logger" \
      description="PDNS logger" \
      url="https://github.com/dmachard/pdns-logger" \
      maintainer="d.machard@gmail.com"
      
WORKDIR /home/pdnslogger

COPY . /home/pdnslogger/

RUN true \
    && adduser -D pdnslogger \
    && pip install --no-cache-dir dnspython protobuf\
    && cd /home/pdnslogger \
    && chmod 755 start.sh \
    && chown -R pdnslogger:pdnslogger /home/pdnslogger \
    && true
    
USER pdnslogger

EXPOSE 50001/tcp

ENTRYPOINT ["/home/pdnslogger/start.sh"]