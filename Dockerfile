FROM python:3.8-alpine

LABEL name="PDNS protobuf receiver" \
      description="PDNS protobuf receiver" \
      url="https://github.com/dmachard/pdns-protobuf-receiver" \
      maintainer="d.machard@gmail.com"
      
WORKDIR /home/pdnspb

COPY . /home/pdnspb/

RUN true \
    && adduser -D pdnspb \
    && pip install --no-cache-dir dnspython protobuf\
    && cd /home/pdnspb \
    && chown -R pdnspb:pdnspb /home/pdnspb \
    && true
    
USER pdnspb

EXPOSE 50001/tcp

ENTRYPOINT ["python", "-c", "import pdns_protobuf_receiver; pdns_protobuf_receiver.start_receiver()"]