#!/usr/bin/python

# MIT License

# Copyright (c) 2020 Denis MACHARD

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import argparse
import binascii
import logging
import asyncio
import socket
import json
import sys

from datetime import datetime, timezone

import dns.rdatatype
import dns.rdataclass
import dns.rdata
import dns.rcode

# wget https://raw.githubusercontent.com/PowerDNS/dnsmessage/master/dnsmessage.proto
# wget https://github.com/protocolbuffers/protobuf/releases/download/v3.12.2/protoc-3.12.2-linux-x86_64.zip
# python3 -m pip install protobuf
# protoc --python_out=. dnstap_pb2.proto

from pdns_protobuf_receiver.dnsmessage_pb2 import PBDNSMessage
from pdns_protobuf_receiver import protobuf

parser = argparse.ArgumentParser()
parser.add_argument(
    "-l",
    default="0.0.0.0:50001",
    help="listen protobuf dns message on tcp/ip address <ip:port>",
)
parser.add_argument("-j", help="write JSON payload to tcp/ip address <ip:port>")
parser.add_argument("-v", action="store_true", help="verbose mode")

PBDNSMESSAGE_TYPE = {
    1: "CLIENT_QUERY",
    2: "CLIENT_RESPONSE",
    3: "AUTH_QUERY",
    4: "AUTH_RESPONSE",
}
PBDNSMESSAGE_SOCKETFAMILY = {1: "IPv4", 2: "IPv6"}

PBDNSMESSAGE_SOCKETPROTOCOL = {1: "UDP", 2: "TCP"}

PBDNSMESSAGE_POLICYTYPE = {
    1: "UNKNOWN",
    2: "QNAME",
    3: "CLIENTIP",
    4: "RESPONSEIP",
    5: "NSDNAME",
    6: "NSDNAME",
}


def get_rdata_attributes(cls, exclude_methods=True):
    """
    Extract attributes to be set in rdata Json Dict

    Extract from dnspython class the attributes that
    will be used to populate the rdata record
    """
    base_attrs = dir(type("dummy", (object,), {}))
    this_cls_attrs = dir(cls)
    res = []
    for attr in this_cls_attrs:
        if base_attrs.count(attr) or (callable(getattr(cls, attr)) and exclude_methods):
            continue
        if attr in ["rdclass", "rdtype", "__slots__"]:
            continue
        res += [attr]
    return res


def parse_pb_msg(dns_pb2, dns_msg):
    """
    Parse Common Fields in Protobuf PowerDNS Messages
    """
    pb_fields_map = {
        "type": ["dns_message", PBDNSMESSAGE_TYPE],  # 1
        "messageId": "message_id",  # 2
        "serverIdentity": "server_identity",  # 3
        "socketFamily": ["socket_family", PBDNSMESSAGE_SOCKETFAMILY],  # 4
        "socketProtocol": ["socket_protocol", PBDNSMESSAGE_SOCKETPROTOCOL],  # 5
        "inBytes": "bytes",  # 8
        "id": "dns_id",  # 11
        # originalRequestorSubnet # 14
        # requestorId # 15
        "initialRequestId": "initial_request_id",  # 16
        "deviceId": "device_id",  # 17
        "newlyObservedDomain": "nod",  # 18
        "deviceName": "device_name",  # 19
        "fromPort": "from_port",  # 20
        "toPort": "to_port",  # 21
    }

    # print(dns_pb2)
    for key, val in pb_fields_map.items():
        if dns_pb2.HasField(key):
            if isinstance(val, str):
                if key in {"messageId", "initialRequestId"}:
                    dns_msg[val] = binascii.hexlify(
                        bytearray(getattr(dns_pb2, key))
                    ).decode()
                else:
                    res = getattr(dns_pb2, key)
                    if isinstance(res, bytes):
                        dns_msg[val] = res.decode()
                    else:
                        dns_msg[val] = res
            else:
                dns_msg[val[0]] = val[1][getattr(dns_pb2, key)]


def parse_pb_msg_query(dns_pb2, dns_msg):
    """
    Parse RRS Fields in Protobuf PowerDNS Messages
    """
    pb_fields_map = {
    }

def parse_pb_msg_response(dns_pb2, dns_msg):
    """
    Parse Response Fields in Protobuf PowerDNS Messages
    """
    pb_fields_map = {
        "rcode": "return_code",  # 1
        "appliedPolicy": "applied_policy",  # 3
        "tags": "tags",  # 4
        "appliedPolicyType": ["applied_policy_type", PBDNSMESSAGE_POLICYTYPE],  # 7
        "appliedPolicyTrigger": "applied_policy_trigger",  # 8
        "appliedPolicyHit": "applied_policy_hit",  # 9
    }

    dns_msg["response"] = {}
    resp = dns_msg["response"]

    for key, val in pb_fields_map.items():
        if key == "tags":
            try:
                tags = []
                for i in getattr(dns_pb2.response, val):
                    tags.append(i)
                if len(tags) > 0:
                    resp["tags"] = tags
            except AttributeError:
                pass
        elif key == "rcode":
            if dns_pb2.response.rcode == 65536:
                dns_msg["response"]["return_code"] = "NETWORK_ERROR"
            else:
                dns_msg["response"]["return_code"] = dns.rcode.to_text(dns_pb2.response.rcode)
        elif dns_pb2.response.HasField(key):
            if isinstance(val, str):
                res = getattr(dns_pb2.response, key)
                resp[val] = res
            else:
                resp[val[0]] = val[1][getattr(dns_pb2.response, key)]


def parse_pb_msg_rrs(dns_pb2, dns_msg):
    """
    Parse RRS Fields in Protobuf PowerDNS Messages
    """
    pb_fields_map = {
        "name": "name",  # 1
        "type": "type",  # 2
        "class": "class",  # 3
        "ttl": "ttl",  # 4
        "rdata": "rdata",  # 5
        "udr": "udr",  # 6
    }

    rrs = []

    for rr in dns_pb2.response.rrs:
        rr_dict = {}
        for key, val in pb_fields_map.items():
            res = getattr(rr, key)
            if key == "rdata":
                rr_dict[val] = {}
                rdata = dns.rdata.from_wire(
                    rr_dict["class"], rr_dict["type"], res, 0, len(res)
                )
                for k in get_rdata_attributes(rdata):
                    rr_dict[val][k] = getattr(rdata, k)
            elif key == "class":
                rr_dict[val] = dns.rdataclass.to_text(res)
            elif key == "type":
                rr_dict[val] = dns.rdatatype.to_text(res)
            else:
                rr_dict[val] = res
        rrs.append(rr_dict)

    if len(rrs) > 0:
        dns_msg["response"]["rrs"] = rrs


async def cb_onpayload(dns_pb2, payload, tcp_writer, debug_mode, loop):
    """on dnsmessage protobuf2"""
    dns_pb2.ParseFromString(payload)

    dns_msg = {}
    parse_pb_msg(dns_pb2, dns_msg)

    dns_msg["from_address"] = "0.0.0.0"
    from_addr = getattr(dns_pb2, "from")
    if len(from_addr):
        if dns_pb2.socketFamily == PBDNSMessage.SocketFamily.INET:
            dns_msg["from_address"] = socket.inet_ntop(socket.AF_INET, from_addr)
        if dns_pb2.socketFamily == PBDNSMessage.SocketFamily.INET6:
            dns_msg["from_address"] = socket.inet_ntop(socket.AF_INET6, from_addr)

    dns_msg["to_address"] = "0.0.0.0"
    to_addr = getattr(dns_pb2, "to")
    if len(to_addr):
        if dns_pb2.socketFamily == PBDNSMessage.SocketFamily.INET:
            dns_msg["to_address"] = socket.inet_ntop(socket.AF_INET, to_addr)
        if dns_pb2.socketFamily == PBDNSMessage.SocketFamily.INET6:
            dns_msg["to_address"] = socket.inet_ntop(socket.AF_INET6, to_addr)

    time_req = 0
    time_rsp = 0
    time_latency = 0

    if dns_pb2.type in [
        PBDNSMessage.Type.DNSQueryType,
        PBDNSMessage.Type.DNSOutgoingQueryType,
    ]:
        utime_req = "%s" % dns_pb2.timeUsec
        time_req = "%s.%s" % (dns_pb2.timeSec, utime_req.zfill(6))

    if dns_pb2.type in [
        PBDNSMessage.Type.DNSResponseType,
        PBDNSMessage.Type.DNSIncomingResponseType,
    ]:
        utime_rsp = "%s" % dns_pb2.timeUsec
        time_rsp = "%s.%s" % (dns_pb2.timeSec, utime_rsp.zfill(6))

        utime_req = "%s" % dns_pb2.response.queryTimeUsec
        time_req = "%s.%s" % (dns_pb2.response.queryTimeSec, utime_req.zfill(6))

        time_latency = round(float(time_rsp) - float(time_req), 6)

        parse_pb_msg_response(dns_pb2, dns_msg)
        parse_pb_msg_rrs(dns_pb2, dns_msg)

    dns_msg["query_time"] = datetime.fromtimestamp(
        float(time_req), tz=timezone.utc
    ).isoformat()
    dns_msg["response_time"] = datetime.fromtimestamp(
        float(time_rsp), tz=timezone.utc
    ).isoformat()

    dns_msg["latency"] = time_latency

    dns_msg["query"] = {}
    dns_msg["query"]["type"] = dns.rdatatype.to_text(dns_pb2.question.qType)
    dns_msg["query"]["name"] = dns_pb2.question.qName

    dns_json = json.dumps(dns_msg)

    if debug_mode:
        logging.info(dns_json)

    else:
        if tcp_writer.transport._conn_lost:
            # exit if we lost the connection with the remote collector
            loop.stop()
            raise Exception("connection lost with remote")

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
            loop.create_task(
                cb_onpayload(dns_pb2, payload, tcp_writer, debug_mode, loop)
            )

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
    logging.basicConfig(
        format="%(asctime)s %(message)s", stream=sys.stdout, level=level
    )

    logging.debug("Start pdns protobuf receiver...")

    try:
        listen_ip, listen_port = args.l.split(":")
    except Exception as e:
        logging.error("bad listen ip:port provided - %s", args.l)
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
            logging.error("bad remote ip:port provided -%s", args.j)
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
    socket_server = asyncio.start_server(
        lambda r, w: cb_onconnect(r, w, tcp_writer, debug_mode),
        host=listen_ip,
        port=listen_port,
    )

    # run until complete
    abstract_server = loop.run_until_complete(socket_server)

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
