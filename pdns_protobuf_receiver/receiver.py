import argparse
import logging
import asyncio
import socket
import json
import sys

import dns.rdatatype
import dns.rcode

from datetime import datetime, timezone

# wget https://raw.githubusercontent.com/PowerDNS/pdns/master/pdns/dnsmessage.proto
# wget https://github.com/protocolbuffers/protobuf/releases/download/v3.12.2/protoc-3.12.2-linux-x86_64.zip
# python3 -m pip install protobuf
# protoc --python_out=. dnstap_pb2.proto

from pdns_protobuf_receiver.dnsmessage_pb2 import PBDNSMessage
from pdns_protobuf_receiver import protobuf

parser = argparse.ArgumentParser()
parser.add_argument("-l",
                    default="0.0.0.0:50001",
                    help="listen protobuf dns message on tcp/ip address <ip:port>")
parser.add_argument("-j",
                    help="write JSON payload to tcp/ip address <ip:port>")
parser.add_argument('-v', action='store_true', help="verbose mode")  

PBDNSMESSAGE_TYPE = { 1: "CLIENT_QUERY", 2: "CLIENT_RESPONSE",
                      3: "AUTH_QUERY", 4: "AUTH_RESPONSE" }
PBDNSMESSAGE_SOCKETFAMILY = { 1: "IPv4", 2: "IPv6" }   

PBDNSMESSAGE_SOCKETPROTOCOL = { 1: "UDP", 2: "TCP" }

async def cb_onpayload(dns_pb2, payload, tcp_writer, debug_mode, loop):
    """on dnsmessage protobuf2"""
    dns_pb2.ParseFromString(payload)

    dns_msg = {}
    dns_msg["dns_message"] = PBDNSMESSAGE_TYPE[dns_pb2.type]
    dns_msg["socket_family"] = PBDNSMESSAGE_SOCKETFAMILY[dns_pb2.socketFamily]
    dns_msg["socket protocol"] = PBDNSMESSAGE_SOCKETPROTOCOL[dns_pb2.socketProtocol]

    dns_msg["from_address"] = "0.0.0.0"
    from_addr = getattr(dns_pb2, 'from')
    if len(from_addr):
        if dns_pb2.socketFamily == PBDNSMessage.SocketFamily.INET:
            dns_msg["from_address"] = socket.inet_ntop(socket.AF_INET, from_addr) 
        if dns_pb2.socketFamily == PBDNSMessage.SocketFamily.INET6:
            dns_msg["from_address"] = socket.inet_ntop(socket.AF_INET6, from_addr)
    
    dns_msg["to_address"] = "0.0.0.0"
    to_addr = getattr(dns_pb2, 'to')
    if len(to_addr):
        if dns_pb2.socketFamily == PBDNSMessage.SocketFamily.INET:
            dns_msg["to_address"] = socket.inet_ntop(socket.AF_INET, to_addr) 
        if dns_pb2.socketFamily == PBDNSMessage.SocketFamily.INET6:
            dns_msg["to_address"] = socket.inet_ntop(socket.AF_INET6, to_addr)
            
    time_req = 0
    time_rsp = 0
    time_latency = 0
    
    if dns_pb2.type in [ PBDNSMessage.Type.DNSQueryType, 
                         PBDNSMessage.Type.DNSOutgoingQueryType]:
        utime_req = "%s" % dns_pb2.timeUsec
        time_req = "%s.%s" % (dns_pb2.timeSec, utime_req.zfill(6) )
  
    if dns_pb2.type in [ PBDNSMessage.Type.DNSResponseType,
                     PBDNSMessage.Type.DNSIncomingResponseType]:
        utime_rsp = "%s" % dns_pb2.timeUsec
        time_rsp = "%s.%s" % (dns_pb2.timeSec, utime_rsp.zfill(6) )

        utime_req = "%s" % dns_pb2.response.queryTimeUsec
        time_req = "%s.%s" % (dns_pb2.response.queryTimeSec, utime_req.zfill(6) )

        time_latency = round(float(time_rsp) - float(time_req), 6)

    dns_msg["query_time"] = datetime.fromtimestamp(float(time_req), tz=timezone.utc).isoformat()
    dns_msg["response_time"] = datetime.fromtimestamp(float(time_rsp), tz=timezone.utc).isoformat()
    
    dns_msg["latency"] = time_latency

    dns_msg["query_type"] = dns.rdatatype.to_text(dns_pb2.question.qType)
    dns_msg["query_name"] = dns_pb2.question.qName

    if dns_pb2.response.rcode == 65536:
        dns_msg["return_code"] = "NETWORK_ERROR"
    else:
        dns_msg["return_code"] = dns.rcode.to_text(dns_pb2.response.rcode)
    dns_msg["bytes"] = dns_pb2.inBytes
    
    dns_json = json.dumps(dns_msg)

    if debug_mode:
       logging.info(dns_json)
    
    else:
        if tcp_writer.transport._conn_lost:
            # exit if we lost the connection with the remote collector
            loop.stop()
            raise Exception("connection lost with remote")
        else:
            tcp_writer.write(dns_json.encode() + b"\n")
     
async def cb_onconnect(reader, writer, tcp_writer, debug_mode):
    logging.debug("connect accepted")
    
    loop = asyncio.get_event_loop()
    protobuf_streamer = protobuf.ProtoBufHandler()
    dns_pb2 = PBDNSMessage()

    running = True
    while running:
        try:
            while not protobuf_streamer.process_data():
                # read data
                data = await reader.read(protobuf_streamer.pending_nb_bytes())
                if not data:
                    break

                # append data to the buffer
                protobuf_streamer.append(data=data)
                
            # dns message is complete so get the payload
            payload = protobuf_streamer.decode()
            
            # create a task to decode it
            loop.create_task(cb_onpayload(dns_pb2, payload, tcp_writer, debug_mode, loop))
            
        except Exception as e:
            running = False
            logging.error("something happened: %s" % e)
    
async def handle_remoteclient(host, port):
    logging.debug("Connecting to %s %s" % (host, port))
    tcp_reader, tcp_writer = await asyncio.open_connection(host, int(port))
    logging.debug("Connected to %s %s" % (host, port))
    return tcp_writer
    
def start_receiver():
    """start dnstap receiver"""
    # parse arguments
    args = parser.parse_args()

    # configure logs
    level = logging.INFO
    if args.v:
        level = logging.DEBUG
    logging.basicConfig(format='%(asctime)s %(message)s',
                        stream=sys.stdout,
                        level=level)

    logging.debug("Start pdns protobuf receiver...")
    
    

    try:
        listen_ip, listen_port = args.l.split(":")
    except Exception as e:
        logging.error("bad listen ip:port provided - %s" % args.l)
        sys.exit(1)

    if args.j is None:
        debug_mode = True
        remote_host = None
        remote_port = None
    else:
        debug_mode = False
        try:
            remote_host, remote_port = args.j.split(":")
        except Exception as e:
            logging.error("bad remote ip:port provided -%s" % args.j)
            sys.exit(1)

    # run until complete
    loop = asyncio.get_event_loop()

    # create connection to the remote json collector ?
    if not debug_mode:
        task = loop.create_task(handle_remoteclient(remote_host, remote_port))
        loop.run_until_complete(task)
        tcp_writer = task.result()
    else:
        tcp_writer = None

    # asynchronous server socket
    socket_server = asyncio.start_server(lambda r,w: cb_onconnect(r, w, 
                                                                  tcp_writer,
                                                                  debug_mode), 
                                         host=listen_ip,
                                         port=listen_port)

    # run until complete
    abstract_server =  loop.run_until_complete(socket_server)
    
    # set some tcp socket options
    sock = abstract_server.sockets[0]
    
    # force to use tcp keepalive    
    # It activates after 1 second (TCP_KEEPIDLE,) of idleness,
    # then sends a keepalive ping once every 3 seconds (TCP_KEEPINTVL),
    # and closes the connection after 10 failed ping (TCP_KEEPCNT)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 10)
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 30)
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 5)

    logging.debug("server listening")
    
    # run event loop
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
        
    if not debug_mode:
        tcp_writer.close()
        logging.debug("connection done")