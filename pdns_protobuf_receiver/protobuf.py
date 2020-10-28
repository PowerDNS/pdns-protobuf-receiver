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

import struct
 
class ProtoBufHandler(object):
    def __init__(self):
        """prepare the class"""
        self.buf = b''
        
        self.datalen = None
        
    def pending_nb_bytes(self):
        """pending number of bytes"""
        if self.datalen is not None:
            return self.datalen
        return 2
        
    def append(self, data):
        """append data to the buffer"""
        self.buf = b''.join([self.buf, data])
         
    def process_data(self):
        """process incoming data"""
        if self.datalen is None:
            # need more data ?
            if len(self.buf) < 2:
                return False 
        
            # enough data, decode frame length
            (self.datalen,) = struct.unpack("!H", self.buf[:2])
            self.buf = self.buf[2:]
            
            # need more data ?
            if len(self.buf) < self.datalen:
                return False
        
            # we have received enough data, the protobuf payload is complete
            return True
            
        else:
            # need more data ?
            if len(self.buf) < self.datalen:
                return False
            
            # we have received enough data, the protobuf payload is complete
            return True
            
    def decode(self):
        """decode"""
        pl = self.buf[:self.datalen]
        self.buf = self.buf[self.datalen:]

        # reset to process next data
        self.datalen = None
        
        return pl
