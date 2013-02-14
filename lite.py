#!/usr/bin/python

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
        self.table_name = None
        self.query_id = None
        self.query = None
        self.fetch_one = False
        self.fetch_all = False
        self.fetch_oid = False
        self.fetch_count = False
        self.parameters = None

    # ##################################################
    # extract
    
    def extract( self ):
        self.database_name = self.extract_request_parameter( 'db' )
        self.config.read( '%s.ini' % self.database_name )
        self.table_name = self.extract_request_parameter( 'tb' )
        self.query_id = self.extract_request_parameter( 'qr' )
        self.query = self.extract_config_parameter( self.table_name, self.query_id )
        self.fetch_one = self.extract_adapter( 'one', [] )
        self.fetch_all = self.extract_adapter( 'all', [ 'SELECT' ] ) and not self.fetch_one
        self.fetch_oid = self.extract_adapter( 'oid', [ 'INSERT' ] )
        self.fetch_count = self.extract_adapter( 'count', [ 'UPDATE', 'DELETE' ] )
        self.parameters = self.extract_query_parameters()

    # ##################################################
    # extract_request_parameter

    def extract_request_parameter( self, key, mandatory=True ):
        if key not in self.request:
            if mandatory:
                raise Exception( 'missing parameter %s' % key )
            return None
        return self.request[ key ].value

    # ##################################################
    # extract_config_parameter

    def extract_config_parameter( self, section, key, mandatory = True ):
        if not self.config.has_section( section ):
            raise Exception( 'missing section %s' % section )
        if not self.config.has_option( section, key ):
            raise Exception( 'missing option %s in section %s' % ( key, section ) )
        return self.config.get( section, key )

    # ##################################################
    # extract_adapter

    def extract_adapter( self, key, query_types ):
        if key is not None:
            regexp = re.compile( '\s*\|\s*%s\s*' % ( key ), re.IGNORECASE )
            if regexp.search( self.query ):
                self.query = regexp.sub( '', self.query )
                return True
        if query_types is not None and len(query_types) > 0 :
            regexp = re.compile( '^\s*(%s)\s*' % ( '|'.join( query_types ) ), re.IGNORECASE )
            if regexp.search( self.query ):
                return True
        return False

    # ##################################################
    # extract_query_parameters

    def extract_query_parameters( self ):
        parameters = []
        regexp = re.compile( '%(\w*)%' )
        match = regexp.search( self.query )
        while match:
            key = match.group(1)
            special_value = ( key in [ 'db', 'tb', 'qr' ] )
            value = self.extract_request_parameter( key, special_value )
            if special_value:
                self.query = regexp.sub( value, self.query, 1 )
            else:
                parameters.append( value )
                self.query = regexp.sub( '?', self.query, 1 )
            match = regexp.search( self.query )
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
            if value is not None:
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
                if value is not None:
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
    
    def __init__( self, request, response ):
        self.request = request
        self.response = response

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
            self.response.error = '%s' % value
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
        # self.response.version = sys.version
        
        with Database( self.request.database_name ) as database:
            
            # execute    
            database.execute( self.request.query, *self.request.parameters )
            
            # fetch oid
            if self.request.fetch_oid:
                self.response[ 'oid' ] = database.fetch_oid()
            
            # fetch count
            if self.request.fetch_count:
                self.response[ 'count' ] = database.fetch_count()
            
            # fetch one row
            if self.request.fetch_one:
                self.response[ 'row' ] = database.fetch_one()
            
            # fetch all rows
            if self.request.fetch_all:
                self.response[ 'rows' ] = database.fetch_all()                


            
# ##################################################
# main
    
if __name__ == '__main__':
    with Usecase( Request(), Response() ) as uc:
        uc.execute()

