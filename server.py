#!/usr/bin/env python3

# Very simple HTTP server for initial development and testing
# This will switch to FastAPI and NGINX soon

from http.server import HTTPServer, SimpleHTTPRequestHandler, test
import sys
import os

class CORSRequestHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        SimpleHTTPRequestHandler.end_headers(self)

if __name__ == '__main__':
    test(CORSRequestHandler, HTTPServer, port=int(sys.argv[1]) if len(sys.argv) > 1 else 8000)
