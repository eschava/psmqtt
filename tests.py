import unittest
from collections import namedtuple
from handlers import *


class TestHandlers(unittest.TestCase):
    def test_tuple_command_handler(self):
        handler = type("TestHandler", (TupleCommandHandler, object),
                       {"get_value": lambda s: namedtuple('test', 'a b')(10, 20)})('test')
        # normal execution
        self.assertEqual(10, handler.handle('a'))
        self.assertEqual({'a': 10, 'b': 20}, handler.handle('*'))
        self.assertEqual("a=10;b=20", handler.handle('*;'))
        # exceptions
        self.assertRaises(Exception, handler.handle, '')
        self.assertRaises(Exception, handler.handle, '/')
        self.assertRaises(Exception, handler.handle, '*/')
        self.assertRaises(Exception, handler.handle, '/*')
        self.assertRaises(Exception, handler.handle, 'blabla')
        self.assertRaises(Exception, handler.handle, 'bla/bla')
        self.assertRaises(Exception, handler.handle, 'bla/')
        self.assertRaises(Exception, handler.handle, '/bla')

    def test_index_tuple_command_handler(self):
        r = [namedtuple('test', 'a b')(1, 2), namedtuple('test', 'a b')(3, 4)]
        handler = type("TestHandler", (IndexTupleCommandHandler, object),
                       {"get_value": lambda s: r})('test')
        # normal execution
        self.assertEqual([1, 3], handler.handle('a/*'))
        self.assertEqual("1;3", handler.handle('a/*;'))
        self.assertEqual(3, handler.handle('a/1'))
        self.assertEqual({'a': 3, 'b': 4}, handler.handle('*/1'))
        self.assertEqual("a=3;b=4", handler.handle('*;/1'))
        # exceptions
        self.assertRaises(Exception, handler.handle, '')
        self.assertRaises(Exception, handler.handle, '*')
        self.assertRaises(Exception, handler.handle, '*;')
        self.assertRaises(Exception, handler.handle, 'a')
        self.assertRaises(Exception, handler.handle, 'a/')
        self.assertRaises(Exception, handler.handle, '/')
        self.assertRaises(Exception, handler.handle, '*/')
        self.assertRaises(Exception, handler.handle, '/*')
        self.assertRaises(Exception, handler.handle, 'blabla')
        self.assertRaises(Exception, handler.handle, 'bla/bla')
        self.assertRaises(Exception, handler.handle, 'bla/')
        self.assertRaises(Exception, handler.handle, '/bla')

    def test_index_or_total_command_handler(self):
        handler = type("TestHandler", (IndexOrTotalCommandHandler, object),
                       {"get_value": lambda s, t: 5 if t else [1, 2, 3]})('test')
        # normal execution
        self.assertEqual(5, handler.handle(''))
        self.assertEqual(1, handler.handle('0'))
        self.assertEqual(3, handler.handle('2'))
        self.assertEqual([1, 2, 3], handler.handle('*'))
        self.assertEqual("1;2;3", handler.handle('*;'))
        # exceptions
        self.assertRaises(Exception, handler.handle, '/')
        self.assertRaises(Exception, handler.handle, '*-')
        self.assertRaises(Exception, handler.handle, '*/')
        self.assertRaises(Exception, handler.handle, '/*')
        self.assertRaises(Exception, handler.handle, '3')
        self.assertRaises(Exception, handler.handle, 'blabla')
        self.assertRaises(Exception, handler.handle, 'bla/bla')
        self.assertRaises(Exception, handler.handle, 'bla/')
        self.assertRaises(Exception, handler.handle, '/bla')

    def test_index_or_total_tuple_command_handler(self):
        total = namedtuple('test', 'a b')(10, 20)
        single = [namedtuple('test', 'a b')(1, 2), namedtuple('test', 'a b')(3, 4)]
        handler = type("TestHandler", (IndexOrTotalTupleCommandHandler, object),
                       {"get_value": lambda s, t: total if t else single})('test')
        # normal execution
        self.assertEqual({'a': 10, 'b': 20}, handler.handle('*'))
        self.assertEqual("a=10;b=20", handler.handle('*;'))
        self.assertEqual(10, handler.handle('a'))
        self.assertEqual([1, 3], handler.handle('a/*'))
        self.assertEqual("1;3", handler.handle('a/*;'))
        self.assertEqual(3, handler.handle('a/1'))
        self.assertEqual({'a': 3, 'b': 4}, handler.handle('*/1'))
        self.assertEqual("a=3;b=4", handler.handle('*;/1'))
        # exceptions
        self.assertRaisesRegexp(Exception, "Element '' in '' is not supported", handler.handle, '')
        self.assertRaises(Exception, handler.handle, '/')
        self.assertRaises(Exception, handler.handle, '*/*')
        self.assertRaises(Exception, handler.handle, '*-')
        self.assertRaises(Exception, handler.handle, '/*')
        self.assertRaises(Exception, handler.handle, '3')
        self.assertRaises(Exception, handler.handle, '/3')
        self.assertRaises(Exception, handler.handle, 'blabla')
        self.assertRaises(Exception, handler.handle, 'bla/bla')
        self.assertRaises(Exception, handler.handle, 'bla/')
        self.assertRaises(Exception, handler.handle, '/bla')
        self.assertRaises(Exception, handler.handle, '*/5')

    def test_disk_usage_command_handler(self):
        disk = '/'
        handler = type("TestHandler", (DiskUsageCommandHandler, object),
                       {"get_value": lambda s,d: self._disk_usage_get_value(disk, d)})('test')
        # normal execution
        self.assertEqual(10, handler.handle('a//'))
        self.assertEqual({'a': 10, 'b': 20}, handler.handle('*//'))
        self.assertEqual("a=10;b=20", handler.handle('*;//'))
        disk = 'c:'
        self.assertEqual(10, handler.handle('a/c:'))
        disk = 'c:/'
        self.assertEqual(10, handler.handle('a/c:/'))
        # exceptions
        disk = None     # do not validate disk, only parameters
        self.assertRaises(Exception, handler.handle, 'a')
        self.assertRaises(Exception, handler.handle, 'a/')
        self.assertRaises(Exception, handler.handle, 'a/')
        self.assertRaises(Exception, handler.handle, '/')
        self.assertRaises(Exception, handler.handle, '*/')
        self.assertRaises(Exception, handler.handle, '/*')
        self.assertRaises(Exception, handler.handle, 'blabla')
        self.assertRaises(Exception, handler.handle, 'bla/bla')
        self.assertRaises(Exception, handler.handle, 'bla/')
        self.assertRaises(Exception, handler.handle, '/bla')

    def _disk_usage_get_value(self, disk, d):
        if disk is not None:
            self.assertEqual(disk, d)
        return namedtuple('test', 'a b')(10, 20)

if __name__ == '__main__':
    unittest.main()