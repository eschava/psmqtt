import unittest
from collections import namedtuple
from handlers import *


class TestHandlers(unittest.TestCase):
    def test_tuple_command_handler(self):
        handler = type("TestHandler", (TupleCommandHandler, object),
                       {"get_value": lambda self: namedtuple('test', 'a b')(10, 20)})('test')
        # normal execution
        self.assertEqual(10, handler.handle('a'))
        self.assertEqual({'a': 10, 'b': 20}, handler.handle('*'))
        # exceptions
        self.assertRaises(Exception, handler.handle, '')
        self.assertRaises(Exception, handler.handle, '/')
        self.assertRaises(Exception, handler.handle, '*/')
        self.assertRaises(Exception, handler.handle, '/*')
        self.assertRaises(Exception, handler.handle, 'blabla')
        self.assertRaises(Exception, handler.handle, 'bla/bla')
        self.assertRaises(Exception, handler.handle, 'bla/')
        self.assertRaises(Exception, handler.handle, '/bla')


if __name__ == '__main__':
    unittest.main()