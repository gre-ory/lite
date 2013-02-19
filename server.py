
# ##################################################
# import

from BaseHTTPServer import HTTPServer
from CGIHTTPServer import CGIHTTPRequestHandler
import cgitb; cgitb.enable()



# ##################################################
# handler

class Handler(CGIHTTPRequestHandler):
    cgi_directories = [ '' ]
    
    def is_cgi( self ):
        if self.path.endswith( '.py' ):
            path = self.path.split( '/' )
            file_name = path.pop() 
            self.cgi_info = ( '%s/' % '/'.join( path ), file_name )
            print '[is_cgi] %s >>> %s ' % ( self.path, self.cgi_info )
            return True
        return False



# ##################################################
# server

url='0.0.0.0'
port=9999
server = HTTPServer( ( url, port ), Handler )
print 'Serving HTTP on %s port %s...' % ( url, port )
server.serve_forever()


