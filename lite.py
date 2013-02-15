#!/usr/bin/python

# ##################################################
# import

import sys
import cgi
import sqlite3
import json
import ConfigParser
import re
import traceback



# ##################################################
# class Query

class Query:

    # ##################################################
    # constructor
    
    def __init__( self, sql=None, parameters=None, fetch_one=None, fetch_all=None, fetch_oid=None, fetch_nb=None ):
        self.sql = sql
        self.parameters = parameters or []
        self.fetch_one = ( fetch_one == True )
        self.fetch_all = ( fetch_all == True )
        self.fetch_oid = ( fetch_oid == True )
        self.fetch_nb = ( fetch_nb == True )
        
    # ##################################################
    # execute
    
    def execute( self, database, response ):
        
        # print '[sql] %s %s' % ( self.sql, self.parameters )
        
        # execute query 
        database.execute_query( self.sql, *self.parameters )
        
        # fetch oid
        if self.fetch_oid:
            response[ 'oid' ] = database.fetch_oid()
        
        # fetch count
        if self.fetch_nb:
            response[ 'nb' ] = database.fetch_nb()
        
        # fetch one row
        if self.fetch_one:
            response[ 'row' ] = database.fetch_one()
        
        # fetch all rows
        if self.fetch_all:
            response[ 'rows' ] = database.fetch_all()



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
    # execute_query

    def execute_query( self, query, *args ):
        if self.connection is None:
            raise Exception( 'database not connected' )
        
        self.cursor = self.connection.cursor()
        
        if len( args ) > 0:
            self.cursor.execute( query, args )
        else:
            self.cursor.execute( query )

    # ##################################################
    # execute_script

    def execute_script( self, script, *args ):
        if self.connection is None:
            raise Exception( 'database not connected' )
        
        self.cursor = self.connection.cursor()
        
        if len( args ) > 0:
            self.cursor.execute( script, args )
            # self.cursor.executescript( script )
        else:
            self.cursor.executescript( script )

    # ##################################################
    # fetch_oid

    def fetch_oid( self ):
        if self.cursor is None:
            raise Exception( 'query not executed' )
        
        return self.cursor.lastrowid

    # ##################################################
    # fetch_nb

    def fetch_nb( self ):
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
# class Request

class Request:

    # ##################################################
    # constructor
    
    def __init__( self ):
        self.parameters = cgi.FieldStorage()
        self.database = None
        self.table = None
        self.multi = False
        self.queries = []

    # ##################################################
    # get_parameter

    def get_parameter( self, key, mandatory=True ):
        if key not in self.parameters:
            if mandatory:
                raise Exception( 'missing parameter %s in request' % key )
            return None
        return self.parameters[ key ].value

    # ##################################################
    # build_query
    
    def build_query( self ):
        
        # extract context
        self.database = self.get_parameter( 'db' )
        self.table = self.get_parameter( 'tb', False )
        sql_query_id = self.get_parameter( 'qr' )
        
        # extract sql_query from config file
        config_file = '%s.ini' % self.database
        config = ConfigParser.ConfigParser()
        config.read( config_file )
        section = self.table or 'DEFAULT'
        if section.upper() != 'DEFAULT' and not config.has_section( section ):
            raise Exception( 'missing section %s in %s' % ( section, config_file ) )
        option = sql_query_id
        if not config.has_option( section, option ):
            raise Exception( 'missing option %s in section %s in %s' % ( option, section, config_file ) )
        sql = config.get( section, option )
        if sql is None:
            raise Exception( 'missing option %s in section %s in %s' % ( option, section, config_file ) )
        
        sql_queries = [ s.strip() for s in sql.split( ';' ) if s.strip() != '' ]
        self.multi = ( len( sql_queries ) > 1 )
        for sql_query in sql_queries:
            # extract sql_parameters from request
            sql_parameters = []
            regexp = re.compile( '%(\w*)%' )
            match = regexp.search( sql_query )
            while match:
                key = match.group(1)
                if key in [ 'db', 'tb' ]:
                    value = self.get_parameter( key )
                    sql_query = regexp.sub( value, sql_query, 1 )
                else:
                    value = self.get_parameter( key, False )
                    sql_parameters.append( value )
                    sql_query = regexp.sub( '?', sql_query, 1 )
                match = regexp.search( sql_query )
            
            # extract sql_fetch
            ( sql_query, fetch_one ) = self.extract_sql_fetch( sql_query, 'one', [] )
            ( sql_query, fetch_all ) = self.extract_sql_fetch( sql_query, 'all', [ 'SELECT' ] )
            ( sql_query, fetch_oid ) = self.extract_sql_fetch( sql_query, 'oid', [ 'INSERT' ] )
            ( sql_query, fetch_nb ) = self.extract_sql_fetch( sql_query, 'nb', [ 'UPDATE', 'DELETE' ] ) 
            
            if self.multi:
                fetch_one = False
                fetch_all = False
                fetch_oid = False
                fetch_nb = False
                
            fetch_all = fetch_all and not fetch_one
            
            # build query
            self.queries.append( Query( sql=sql_query, parameters=sql_parameters, fetch_one=fetch_one, fetch_all=fetch_all, fetch_oid=fetch_oid, fetch_nb=fetch_nb ) )

    # ##################################################
    # extract_sql_fetch

    def extract_sql_fetch( self, sql_query, fetch_id, sql_query_types ):
        
        # extract sql_fetch from fetch_id
        regexp = re.compile( '\s*\|\s*%s\s*' % ( fetch_id ), re.IGNORECASE )
        if regexp.search( sql_query ):
            sql_query = regexp.sub( '', sql_query )
            return ( sql_query, True )
        
        # extract sql_fetch from sql_query_types
        if len( sql_query_types ) > 0 :
            regexp = re.compile( '^\s*(%s)\s*' % ( '|'.join( sql_query_types ) ), re.IGNORECASE )
            if regexp.search( sql_query ):
                return ( sql_query, True )
        
        return ( sql_query, False )


        
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
        pass

    # ##################################################
    # dump
    
    def dump( self ):
        pass



# ##################################################
# class JsonResponse

class JsonResponse( Response ):

    # ##################################################
    # header
    
    def dump_header( self ):
        print 'Content-Type: text/json'
        print

    # ##################################################
    # dump_body
    
    def dump( self ):
        print json.dumps( self.__dict__, sort_keys=True, indent=4, separators=( ',', ': ' ) )



# ##################################################
# class Usecase

class Usecase:

    # ##################################################
    # constructor
    
    def __init__( self, request=None, response=None ):
        self.request = request or Request()
        self.response = response or Response()

    # ##################################################
    # set up

    def __enter__( self ):
        self.response.dump_header()
        return self

    # ##################################################
    # tear down
        
    def __exit__( self, type, value, stack ):
        if value is not None:
            # print '[error] %s %s ' % ( type, value )
            # traceback.print_tb( stack, file=sys.stdout )
            self.response.success = False
            self.response.error = '%s' % value
        else:
            self.response.success = True
        self.response.dump()
        return False

    # ##################################################
    # execute
    
    def execute( self ):

        # prepare sql query
        self.request.build_query()
        
        with Database( self.request.database ) as database:
        
            # execute sql queries
            for query in self.request.queries:
                query.execute( database, self.response )
            
# ##################################################
# main
    
if __name__ == '__main__':
    with Usecase( response=JsonResponse() ) as uc:
        uc.execute()

