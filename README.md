# PDNS protobuf logger to JSON stream

![](https://github.com/dmachard/pdns_logger/workflows/Publish%20to%20PyPI/badge.svg)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/pdns_logger)

| | |
| ------------- | ------------- |
| Author |  Denis Machard <d.machard@gmail.com> |
| License |  MIT | 
| PyPI |  https://pypi.org/project/pdns_logger/ |
| | |

PDNS logger is a daemon in Python 3 that acts a protobuf server for PowerDNS's products.
You can use it to collect DNS queries and responses and to log to syslog or a json remote tcp collector.

## Table of contents
* [Installation](#installation)
* [Exectute pdns logger](#exectute-pdns-logger)
* [Startup options](#startup-options)
* [Output JSON format](#output-json-format)
* [Systemd service file configuration](#systemd-service-file-configuration)
* [Usages](#usages)

## Installation

Deploy the pdns logger with the pip command.

```python
pip install pdns_logger
```

## Execute pdns logger 

To run the pdns logger, execute the following command without arguments. 

```
# pdns_logger
2020-05-29 18:39:08,579 Start pdns logger...
2020-05-29 18:39:08,580 Using selector: EpollSelector
```

In this mode, the logger is listening by default on the 0.0.0.0 interface and 50000 tcp port and 
DNS queries and responses are also printed directly on stdout in JSON format.

If you want to send your DNS logs to a remote JSON collector, start the pdns logger as below.

```
# pdns_logger -j 10.0.0.235:6000
2020-05-29 18:39:08,579 Start pdns logger...
2020-05-29 18:39:08,580 Using selector: EpollSelector
2020-05-29 18:39:08,580 Connecting to 10.0.0.235 6000
2020-05-29 18:39:08,585 Connected to 10.0.0.235 6000
```

## Startup options

```
optional arguments:
  -h, --help  show this help message and exit
  -l L        listen protobuf dns message on tcp/ip address <ip:port>
  -j J        write JSON payload to tcp/ip address <ip:port>
```

## Output JSON format

```json
{
    'dns_message': 'AUTH_QUERY',
    'socket_family': 'INET',
    'socket protocol': 'UDP',
    'from_address': '0.0.0.0',
    'to_address': '184.26.161.130',
    'query_time': '2020-05-29 13:46:23.322',
    'response_time': '1970-01-01 01:00:00.000',
    'latency': 0,
    'query_type': 'A',
    'query_name': 'a13-130.akagtm.org.',
    'return_code': 'NOERROR',
    'bytes': 4
}
```

## Systemd service file configuration

System service file for Centos7

```bash
vim /etc/systemd/system/dnstap_receiver.service

[Unit]
Description=Python DNS tap Service
After=network.target

[Service]
ExecStart=/usr/local/bin/dnstap_receiver -u /etc/dnsdist/dnstap.sock -j 10.0.0.2:6000
Restart=on-abort
Type=simple
User=root

[Install]
WantedBy=multi-user.target
```

```bash
systemctl daemon-reload
systemctl start dnstap_receiver
systemctl status dnstap_receiver
systemctl enable dnstap_receiver
```

## Usages

### collect logs from dnsdist

vim /etc/dnsdist/dnsdist.conf

```
rl = newRemoteLogger("10.0.0.97:50000")
addAction(AllRule(),RemoteLogAction(rl))
addResponseAction(AllRule(),RemoteLogResponseAction(rl))
```

### collect logs from pdns-recursor

vim /etc/pdns-recursor/recursor.conf

```
lua-config-file=/etc/pdns-recursor/recursor.lua
```

vim /etc/pdns-recursor/recursor.lua

```
protobufServer("10.0.0.97:50000", {logQueries=true, logResponses=true, exportTypes={'A', 'AAAA', 'CNAME', 'MX', 'PTR', 'NS', 'SPF', 'SRV', 'TXT'}} )
outgoingProtobufServer("10.0.0.97:50000",  {logQueries=true, logResponses=true, exportTypes={'A', 'AAAA', 'CNAME', 'MX', 'PTR', 'NS', 'SPF', 'SRV', 'TXT'}})
```

### collect logs and send-it to ELK

vim /etc/logstash/conf.d/pdns-logger.conf

```
input {
  tcp {
      port => 50000
      codec => json
  }
}

filter {
  date {
     match => [ "dt_query" , "yyyy-MM-dd HH:mm:ss.SSS" ]
     target => "@timestamp"
  }
}

output {
   elasticsearch {
    hosts => ["http://localhost:9200"]
    index => "pdns-logger"
  }
}
```
