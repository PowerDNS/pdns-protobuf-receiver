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
