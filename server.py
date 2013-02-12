
# ##################################################
# import

from BaseHTTPServer import HTTPServer
from CGIHTTPServer import CGIHTTPRequestHandler
import cgitb; cgitb.enable()



# ##################################################
# handler

class Handler(CGIHTTPRequestHandler):
    cgi_directories = [ '/' ]



# ##################################################
# server

url='0.0.0.0'
port=9999
server = HTTPServer( ( url, port ), Handler )
print 'Serving HTTP on %s port %s...' % ( url, port )
server.serve_forever()


