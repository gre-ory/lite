
# ##################################################
# import

import sys
import cgi
import sqlite3
import json
import ConfigParser
import re



# ##################################################
# class Request

class Request:

    # ##################################################
    # constructor
    
    def __init__( self ):
        self.request = cgi.FieldStorage()
        self.config = ConfigParser.ConfigParser()
        self.database_name = None
        self.query_id = None
        self.query = None
        self.fetch_one = None
        self.fetch_all = None
        self.parameters = None

    # ##################################################
    # extract
    
    def extract( self ):
        self.config.read( 'lite.ini' )
        self.database_name = self.extract_from_request( 'db' )
        self.query_id = self.extract_from_request( 'query' )
        self.query = self.extract_from_config( self.database_name, self.query_id )
        self.fetch_one = self.extract_fetch( 'one', 'item' )
        self.fetch_all = self.extract_fetch( 'all', 'items' )
        self.parameters = self.extract_parameters_from_query()

    # ##################################################
    # extract_from_request

    def extract_from_request( self, key ):
        if key not in self.request:
            raise Exception( 'missing parameter %s' % key )
        return self.request[ key ].value

    # ##################################################
    # extract_from_config

    def extract_from_config( self, section, key, mandatory = True ):
        if not self.config.has_section( section ):
            raise Exception( 'missing section %s' % section )
        if not self.config.has_option( section, key ):
            raise Exception( 'missing option %s in section %s' % ( key, section ) )
        return self.config.get( section, key )

    # ##################################################
    # extract_fetch

    def extract_fetch( self, key, default_value ):
        pattern = '\s*\|\s*%s\s*\|\s*(\w+)\s*$' % key
        match = re.search( pattern, self.query, re.IGNORECASE )
        if match:
            value = match.group(1)
            self.query = re.sub( pattern, '', self.query, 1, re.IGNORECASE )
            if value is None or value == '':
                return default_value
            return value
        pattern = '\s*\|\s*%s\s*$' % key
        match = re.search( pattern, self.query, re.IGNORECASE )
        if match:
            self.query = re.sub( pattern, '', self.query, 1, re.IGNORECASE )
            return default_value
        return None

    # ##################################################
    # extract_parameters_from_query

    def extract_parameters_from_query( self ):
        pattern = '%(\w*)%'
        parameters = []
        match = re.search( pattern, self.query )
        while match:
            key = match.group(1)
            value = self.extract_from_request( key )
            parameters.append( value )
            self.query = re.sub( pattern, '?', self.query, 1 )
            match = re.search( pattern, self.query )
        return parameters



# ##################################################
# class Database

class Database:
    
    # ##################################################
    # constructor
    
    def __init__( self, name ):
        self.name = name
        self.connection = None

    # ##################################################
    # set up
    
    def __enter__( self ):
        self.connect()
        return self

    # ##################################################
    # tear dow
      
    def __exit__( self, type, value, traceback ):
        if self.connection is not None:
            if value is not None:
                self.rollback()
            else:
                self.commit()
            self.disconnect()

    # ##################################################
    # connect
    
    def connect( self ):
        if self.name is None:
            raise Exception( 'missing database name' )
        self.connection = sqlite3.connect( '%s.db' % self.name )

    # ##################################################
    # disconnect
    
    def disconnect( self ):
        if self.connection is not None:
            self.connection.close()
        self.connection = None

    # ##################################################
    # commit

    def commit( self ):
        if self.connection is not None:
            self.connection.commit()

    # ##################################################
    # rollback
    
    def rollback( self ):
        if self.connection is not None:
            self.connection.rollback()

    # ##################################################
    # execute

    def execute( self, query, *args ):
        if self.connection is None:
            raise Exception( 'database not connected' )
        
        self.cursor = self.connection.cursor()
            
        if query.find( ';' ) != -1:
            if len( args ):
                self.cursor.executescript( query, args )
            else:
                self.cursor.executescript( query )
        else:
            if len( args ):
                self.cursor.execute( query, args )
            else:
                self.cursor.execute( query )

    # ##################################################
    # fetch_oid

    def fetch_oid( self ):
        if self.cursor is None:
            raise Exception( 'query not executed' )
        
        return self.cursor.lastrowid

    # ##################################################
    # fetch_count

    def fetch_count( self ):
        if self.cursor is None:
            raise Exception( 'query not executed' )
        
        if self.cursor.rowcount >= 0:
            return self.cursor.rowcount
        return None

    # ##################################################
    # fetch_one

    def fetch_one( self ):
        if self.cursor is None:
            raise Exception( 'query not executed' )
        
        if self.cursor.description is None:
            raise Exception( 'query failed' )
        
        row = self.cursor.fetchone()
        if row is None:
            raise Exception( 'row not found' )
            
        item = {}
        keys = [ column[0] for column in self.cursor.description ]
        index = 0
        for value in row:
            item[ keys[ index ] ] = value
            index = index + 1
        return item

    # ##################################################
    # fetch_all
    
    def fetch_all( self ):
        if self.cursor is None:
            raise Exception( 'query not executed' )
        
        if self.cursor.description is None:
            raise Exception( 'query failed' )
        
        items = []
        keys = [ column[0] for column in self.cursor.description ]
        for row in self.cursor.fetchall():
            item = {}
            index = 0
            for value in row:
                item[ keys[ index ] ] = value
                index = index + 1
            items.append( item )
        
        return items



# ##################################################
# class Response

class Response:

    # ##################################################
    # constructor
    
    def __init__( self ):
        pass

    # ##################################################
    # set
    
    def __setitem__( self, key, value ):
        self.__dict__[ key ] = value

    # ##################################################
    # dump_header
    
    def dump_header( self ):
        print 'Content-Type: text/json'
        print

    # ##################################################
    # dump
    
    def dump( self ):
        print json.dumps( self.__dict__, sort_keys=True, indent=4, separators=( ',', ': ' ) )



# ##################################################
# class Usecase

class Usecase:

    # ##################################################
    # constructor
    
    def __init__( self ):
        self.request = Request()
        self.response = Response()

    # ##################################################
    # set up

    def __enter__( self ):
        self.response.dump_header()
        return self

    # ##################################################
    # tear down
        
    def __exit__( self, type, value, traceback ):
        if value is not None:
            self.response.success = False
            self.response.error = value.args[0]
        else:
            self.response.success = True
        self.response.dump()
        return False

    # ##################################################
    # execute
    
    def execute( self ):
        
        # extract
        self.request.extract()
        # self.response.query = self.request.query
        # self.response.parameters = self.request.parameters
        
        with Database( self.request.database_name ) as database:
            
            # execute    
            database.execute( self.request.query, *self.request.parameters )
            
            # fetch oid
            oid = database.fetch_oid()
            if oid is not None:
                self.response[ 'oid' ] = oid
            
            # fetch count
            count = database.fetch_count()
            if count is not None:
                self.response[ 'count' ] = count
            
            # fetch item
            if self.request.fetch_one is not None:
                value = database.fetch_one()
                self.response[ self.request.fetch_one ] = value
            
            # fetch items
            if self.request.fetch_all is not None:
                value = database.fetch_all()
                self.response[ self.request.fetch_all ] = value
            


# ##################################################
# execute

with Usecase() as uc:
    uc.execute()

