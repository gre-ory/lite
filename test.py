#!/usr/bin/python

# ##################################################
# import

import lite
import unittest
import sys
import cgi
import os



# ##################################################
# class FakeResponse

class FakeResponse:

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
# lite unittest

class LiteUnitTest( unittest.TestCase ):
    
    # ##################################################
    # execute
    
    def execute( self, db='test', tb='test', **kwargs ):
        if db is not None:
            kwargs[ 'db' ] = db
        if tb is not None:
            kwargs[ 'tb' ] = tb
        os.environ[ 'QUERY_STRING' ] = '&'.join( [ '%s=%s' % ( key, kwargs[key] ) for key in kwargs ] )
        os.environ[ 'REQUEST_METHOD' ] = 'GET'
        self.request = lite.Request()
        self.response = FakeResponse()
        try:
            with lite.Usecase( self.request, self.response ) as usecase:
                usecase.execute()
        except:
            pass

    # ##################################################
    # request

    def assert_request( self, query=None, parameters=[], fetch_one=False, fetch_all=False, fetch_oid=False, fetch_count=False, database_name='test' ):
        self.request.extract()
        self.assertEqual( self.request.database_name, database_name )
        self.assertEqual( self.request.query, query )
        self.assertEqual( self.request.fetch_one, fetch_one )
        self.assertEqual( self.request.fetch_all, fetch_all )
        self.assertEqual( self.request.fetch_oid, fetch_oid )
        self.assertEqual( self.request.fetch_count, fetch_count )
        self.assertEqual( len(self.request.parameters), len(parameters) )
        for i, parameter in enumerate(parameters):
            self.assertEqual( self.request.parameters[i], parameter )

    # ##################################################
    # response

    def assert_response( self, success, error=None, oid=None, row=None, rows=None, count=None  ):
        self.assertEqual( self.response.success, success )
        if error is not None:
            self.assertEqual( self.response.error, error )
        if oid is not None:
            self.assertEqual( self.response.oid, oid )
        if row is not None:
            self.assertEqual( self.response.row, row )
        if rows is not None:
            self.assertEqual( self.response.rows, rows )
        if count is not None:
            self.assertEqual( self.response.count, count )

    # ##################################################
    # test
    
    def test_00_drop_table( self ):
        self.execute( qr='drop.table' )
        self.assert_request( 'DROP TABLE IF EXISTS test' )
        self.assert_response( True )

    def test_01_create_table( self ):
        self.execute( qr='create.table' )
        self.assert_request( 'CREATE TABLE test ( oid INTEGER PRIMARY KEY, key TEXT NOT NULL, value TEXT )' )
        self.assert_response( True )

    def test_10_insert( self ):
        self.execute( qr='insert', key='one', value='un' )
        self.assert_request( 'INSERT INTO test ( key, value ) VALUES ( ?, ? )', [ 'one', 'un' ], fetch_oid = True )
        self.assert_response( True, oid=1 )

    def test_11_insert( self ):
        self.execute( qr='insert', key='two', value='deux' )
        self.assert_request( 'INSERT INTO test ( key, value ) VALUES ( ?, ? )', [ 'two', 'deux' ], fetch_oid = True )
        self.assert_response( True, oid=2 )

    def test_12_insert( self ):
        self.execute( qr='insert', key='two', value='duo' )
        self.assert_request( 'INSERT INTO test ( key, value ) VALUES ( ?, ? )', [ 'two', 'duo' ], fetch_oid = True )
        self.assert_response( True, oid=3 )
    
    def test_13_insert_with_missing_key( self ):
        self.execute( qr='insert', value='something' )
        self.assert_request( 'INSERT INTO test ( key, value ) VALUES ( ?, ? )', [ None, 'something' ], fetch_oid = True )
        self.assert_response( False, error='test.key may not be NULL', oid=None )
        
    def test_20_missing_parameter( self ):
        self.execute( qr='select.one' )
        self.assert_request( 'SELECT * FROM test WHERE oid = ?', [ None ], fetch_one = True )
        self.assert_response( False, error='row not found' )
        
    def test_21_select_one( self ):
        self.execute( qr='select.one', oid='1' )
        self.assert_request( 'SELECT * FROM test WHERE oid = ?', [ '1' ], fetch_one = True )
        self.assert_response( True, row={'oid': 1, 'value': 'un', 'key': 'one'} )

    def test_22_select_one_ignorecase( self ):
        self.execute( qr='select.one.ignorecase', oid='1' )
        self.assert_request( 'SELECT * FROM test WHERE oid = ?', [ '1' ], fetch_one = True )
        self.assert_response( True, row={'oid': 1, 'value': 'un', 'key': 'one'} )

    def test_23_select_all( self ):
        self.execute( qr='select.all' )
        self.assert_request( 'SELECT * FROM test', fetch_all = True )
        self.assert_response( True, rows=[{'oid': 1, 'value': 'un', 'key': 'one'}, {'oid': 2, 'value': 'deux', 'key': 'two'}, {'oid': 3, 'value': 'duo', 'key': 'two'}] )

    def test_24_count( self ):
        self.execute( qr='count', key='one' )
        self.assert_request( 'SELECT COUNT(*) AS nb FROM test WHERE key = ?', [ 'one' ], fetch_one = True, fetch_oid = True, fetch_count = True  )
        self.assert_response( True, row={'nb': 1} )

    def test_25_select_one( self ):
        self.execute( qr='select.one', oid='99' )
        self.assert_request( 'SELECT * FROM test WHERE oid = ?', [ '99' ], fetch_one = True )
        self.assert_response( False, error='row not found' )
                
    def test_30_update( self ):
        self.execute( qr='update', key='one', value='uno' )
        self.assert_request( 'UPDATE test SET value = ? WHERE key = ?', [ 'uno', 'one' ], fetch_count = True )
        self.assert_response( True, count=1 )

    def test_31_select_one( self ):
        self.execute( qr='select.one', oid='1' )
        self.assert_request( 'SELECT * FROM test WHERE oid = ?', [ '1' ], fetch_one = True )
        self.assert_response( True, row={'oid': 1, 'value': 'uno', 'key': 'one'} )
        
    def test_40_delete( self ):
        self.execute( qr='delete', oid='1' )
        self.assert_request( 'DELETE FROM test WHERE oid = ?', [ '1' ], fetch_count = True )
        self.assert_response( True, count=1 )

    def test_41_delete_all( self ):
        self.execute( qr='delete.all' )
        self.assert_request( 'DELETE FROM test', fetch_count = True )
        self.assert_response( True, count=2 )

    def test_90_missing_db( self ):
        self.execute( db=None, qr='drop' )
        self.assert_response( False, error='missing parameter db' )

    def test_92_missing_table( self ):
        self.execute( tb=None, qr='drop' )
        self.assert_response( False, error='missing parameter tb' )
        
    def test_91_missing_query( self ):
        self.execute()
        self.assert_response( False, error='missing parameter qr' )




# ##################################################
# main

if __name__ == '__main__':
    print 'Content-Type: text/text'
    print
    suite = unittest.TestLoader().loadTestsFromTestCase( LiteUnitTest )
    unittest.TextTestRunner( stream=sys.stdout, verbosity = 2 ).run( suite )

