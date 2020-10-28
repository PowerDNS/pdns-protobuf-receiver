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

import time
import unittest
import subprocess
import dns.resolver

my_resolver = dns.resolver.Resolver(configure=False)
my_resolver.nameservers = ['127.0.0.1']

class TestStdout(unittest.TestCase):
    def test1_listening(self):
        """test listening tcp socket"""
        cmd = ["python3", "-c", 
               "import pdns_protobuf_receiver; pdns_protobuf_receiver.start_receiver()", "-v"]
        with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT) as proc:
            time.sleep(2)
            proc.kill()
            
            o = proc.stdout.read()
            print(o)
        self.assertRegex(o, b"listening")
        
    def test2_protobuf(self):
        """test to receive protobuf message"""
        cmd = ["python3", "-c", 
               "import pdns_protobuf_receiver; pdns_protobuf_receiver.start_receiver()", "-v"]

        with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT) as proc:
            for i in range(10):
                r = my_resolver.resolve('www.github.com', 'a')
                time.sleep(1)

            proc.kill()
            
            o = proc.stdout.read()
            print(o)
        self.assertRegex(o, b"CLIENT_QUERY")
        