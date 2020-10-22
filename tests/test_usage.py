
import time
import unittest
import subprocess
import dns.resolver


class TestUsage(unittest.TestCase):
    def test1_print_usage(self):
        """test print usage"""
        cmd = ["python3", "-c", 
               "import pdns_protobuf_receiver; pdns_protobuf_receiver.start_receiver()", 
               "-h"]
        with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT) as proc:
            o = proc.stdout.read()
            print(o)
        self.assertRegex(o, b"show this help message and exit")