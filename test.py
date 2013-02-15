#!/usr/bin/python

# ##################################################
# import

import lite
import unittest
import sys
import cgi
import os

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
        # print '\n [rq] %s' % os.environ[ 'QUERY_STRING' ]
        os.environ[ 'REQUEST_METHOD' ] = 'GET'
        try:
            with lite.Usecase( lite.Request(), lite.Response() ) as self.usecase:
                self.usecase.execute()
        except:
            pass
        self.index = 0

    # ##################################################
    # assert_query

    def assert_query( self, sql=None, parameters=[], fetch_one=False, fetch_all=False, fetch_oid=False, fetch_nb=False, table='test', database='test' ):
        self.assertTrue( self.usecase is not None )
        self.assertTrue( self.usecase.request is not None )
        self.assertEqual( self.usecase.request.database, database )
        self.assertEqual( self.usecase.request.table, table )
        self.assertEqual( self.usecase.request.multi, len(self.usecase.request.queries) > 1 )
        self.assertTrue( self.index < len(self.usecase.request.queries) )
        query = self.usecase.request.queries[ self.index ]
        self.assertTrue( query is not None )
        self.assertEqual( query.sql, sql )
        self.assertEqual( len(query.parameters), len(parameters) )
        for i, parameter in enumerate(parameters):
            self.assertEqual( query.parameters[i], parameter )
        self.assertEqual( query.fetch_one, fetch_one )
        self.assertEqual( query.fetch_all, fetch_all )
        self.assertEqual( query.fetch_oid, fetch_oid )
        self.assertEqual( query.fetch_nb, fetch_nb )
        self.index = self.index + 1

    # ##################################################
    # assert_response

    def assert_response( self, success, error=None, oid=None, row=None, rows=None, nb=None  ):
        self.assertEqual( self.usecase.response.success, success )
        if error is not None:
            self.assertEqual( self.usecase.response.error, error )
        if oid is not None:
            self.assertEqual( self.usecase.response.oid, oid )
        if row is not None:
            self.assertEqual( self.usecase.response.row, row )
        if rows is not None:
            self.assertEqual( self.usecase.response.rows, rows )
        if nb is not None:
            self.assertEqual( self.usecase.response.nb, nb )

    # ##################################################
    # test
    
    def test_00_drop( self ):
        self.execute( qr='drop' )
        self.assert_query( 'DROP TABLE test' )
        self.assert_query( 'DROP TABLE tmp' )
        self.assert_response( True )

    def test_01_create( self ):
        self.execute( qr='create' )
        self.assert_query( 'CREATE TABLE test ( oid INTEGER PRIMARY KEY, key TEXT NOT NULL, value TEXT )' )
        self.assert_query( 'CREATE TABLE tmp ( oid INTEGER PRIMARY KEY, key TEXT NOT NULL, value TEXT )' )
        self.assert_response( True )

    def test_10_insert( self ):
        self.execute( qr='insert', key='one', value='un' )
        self.assert_query( 'INSERT INTO test ( key, value ) VALUES ( ?, ? )', [ 'one', 'un' ], fetch_oid = True )
        self.assert_response( True, oid=1 )

    def test_11_insert( self ):
        self.execute( qr='insert', key='two', value='deux' )
        self.assert_query( 'INSERT INTO test ( key, value ) VALUES ( ?, ? )', [ 'two', 'deux' ], fetch_oid = True )
        self.assert_response( True, oid=2 )

    def test_12_insert( self ):
        self.execute( qr='insert', key='two', value='duo' )
        self.assert_query( 'INSERT INTO test ( key, value ) VALUES ( ?, ? )', [ 'two', 'duo' ], fetch_oid = True )
        self.assert_response( True, oid=3 )
    
    def test_13_insert_with_missing_key( self ):
        self.execute( qr='insert', value='something' )
        self.assert_query( 'INSERT INTO test ( key, value ) VALUES ( ?, ? )', [ None, 'something' ], fetch_oid = True )
        self.assert_response( False, error='test.key may not be NULL', oid=None )

    def test_14_upsert( self ):
        self.execute( qr='upsert', key='three', value='three' )
        self.assert_query( 'DELETE FROM test WHERE key = ?', [ 'three' ] )
        self.assert_query( 'INSERT INTO test ( key, value ) VALUES ( ?, ? )', [ 'three', 'three' ] )
        self.assert_response( True )

    def test_15_upsert( self ):
        self.execute( qr='upsert', key='three', value='trois' )
        self.assert_query( 'DELETE FROM test WHERE key = ?', [ 'three' ] )
        self.assert_query(  'INSERT INTO test ( key, value ) VALUES ( ?, ? )', [ 'three', 'trois' ] )
        self.assert_response( True )
                        
    def test_20_missing_parameter( self ):
        self.execute( qr='select.one' )
        self.assert_query( 'SELECT * FROM test WHERE oid = ?', [ None ], fetch_one = True )
        self.assert_response( False, error='row not found' )
        
    def test_21_select_one( self ):
        self.execute( qr='select.one', oid='1' )
        self.assert_query( 'SELECT * FROM test WHERE oid = ?', [ '1' ], fetch_one = True )
        self.assert_response( True, row={'oid': 1, 'value': 'un', 'key': 'one'} )

    def test_22_select_one_ignorecase( self ):
        self.execute( qr='select.one.ignorecase', oid='1' )
        self.assert_query( 'SELECT * FROM test WHERE oid = ?', [ '1' ], fetch_one = True )
        self.assert_response( True, row={'oid': 1, 'value': 'un', 'key': 'one'} )

    def test_23_select_all( self ):
        self.execute( qr='select.all' )
        self.assert_query( 'SELECT * FROM test', fetch_all = True )
        self.assert_response( True, rows=[{'oid': 1, 'value': u'un', 'key': u'one'}, {'oid': 2, 'value': u'deux', 'key': u'two'}, {'oid': 3, 'value': u'duo', 'key': u'two'}, {'oid': 4, 'value': u'trois', 'key': u'three'}] )

    def test_24_count( self ):
        self.execute( qr='count', key='one' )
        self.assert_query( 'SELECT COUNT(*) AS nb FROM test WHERE key = ?', [ 'one' ], fetch_one = True, fetch_oid = True, fetch_nb = True  )
        self.assert_response( True, row={'nb': 1} )

    def test_25_select_one( self ):
        self.execute( qr='select.one', oid='99' )
        self.assert_query( 'SELECT * FROM test WHERE oid = ?', [ '99' ], fetch_one = True )
        self.assert_response( False, error='row not found' )
                
    def test_30_update( self ):
        self.execute( qr='update', key='one', value='uno' )
        self.assert_query( 'UPDATE test SET value = ? WHERE key = ?', [ 'uno', 'one' ], fetch_nb = True )
        self.assert_response( True, nb=1 )

    def test_31_select_one( self ):
        self.execute( qr='select.one', oid='1' )
        self.assert_query( 'SELECT * FROM test WHERE oid = ?', [ '1' ], fetch_one = True )
        self.assert_response( True, row={'oid': 1, 'value': 'uno', 'key': 'one'} )
        
    def test_40_delete( self ):
        self.execute( qr='delete', oid='1' )
        self.assert_query( 'DELETE FROM test WHERE oid = ?', [ '1' ], fetch_nb = True )
        self.assert_response( True, nb=1 )

    def test_41_select_all( self ):
        self.execute( qr='select.all' )
        self.assert_query( 'SELECT * FROM test', fetch_all = True )
        self.assert_response( True, rows=[{'oid': 2, 'value': u'deux', 'key': u'two'}, {'oid': 3, 'value': u'duo', 'key': u'two'}, {'oid': 4, 'value': u'trois', 'key': u'three'}] )
        
    def test_42_delete_all( self ):
        self.execute( qr='delete.all' )
        self.assert_query( 'DELETE FROM test WHERE 1=1', fetch_nb = True )
        self.assert_response( True, nb=3 )

    def test_43_select_all( self ):
        self.execute( qr='select.all' )
        self.assert_query( 'SELECT * FROM test', fetch_all = True )
        self.assert_response( True, rows=[] )

    def test_90_missing_db( self ):
        self.execute( db=None, qr='count' )
        self.assert_response( False, error='missing parameter db in request' )

    def test_91_missing_tb( self ):
        self.execute( tb=None, qr='count' )
        self.assert_response( False, error='missing option count in section DEFAULT in test.ini' )
        
    def test_92_missing_tb( self ):
        self.execute( tb=None, qr='select.all' )
        self.assert_response( False, error='missing parameter tb in request' )

    def test_93_missing_query( self ):
        self.execute()
        self.assert_response( False, error='missing parameter qr in request' )




# ##################################################
# main

if __name__ == '__main__':
    print 'Content-Type: text/text'
    print
    if True:
        suite = unittest.TestLoader().loadTestsFromTestCase( LiteUnitTest )
        unittest.TextTestRunner( stream=sys.stdout, verbosity = 2 ).run( suite )
    else:
        suite = LiteUnitTest( 'test_15_upsert' )
        suite.test_15_upsert()

