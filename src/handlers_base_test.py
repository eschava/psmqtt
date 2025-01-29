# Copyright (c) 2016 psmqtt project
# Licensed under the MIT License.  See LICENSE file in the project root for full license information.

import unittest
from collections import namedtuple
import pytest

from .handlers_base import (
    IndexCommandHandler,
    IndexOrTotalCommandHandler,
    IndexOrTotalTupleCommandHandler,
    IndexTupleCommandHandler,
    NameOrTotalTupleCommandHandler,
    TupleCommandHandler,
    ValueCommandHandler,
)

@pytest.mark.unit
class TestHandlers(unittest.TestCase):

    def test_value_command_handler(self) -> None:
        handler = type(
            "TestHandler",
            (ValueCommandHandler, object),
            {"get_value": lambda s: 50})('test')
        # normal execution
        self.assertEqual(50, handler.handle([]))
        # exceptions
        self.assertRaises(Exception, handler.handle, ['a'])
        self.assertRaises(Exception, handler.handle, ['/'])
        self.assertRaises(Exception, handler.handle, ['*'])

    def test_ValueCommandHandler(self) -> None:
        handler = ValueCommandHandler("cpu_percent")
        # normal execution
        val = handler.handle([])
        self.assertIsInstance(val, float)
        # exceptions
        self.assertRaises(Exception, handler.handle, ['a'])

        return

    def test_index_command_handler(self) -> None:
        handler = type(
            "TestHandler",
            (IndexCommandHandler, object),
            {"get_value": lambda s: [5, 6, 7]})('test')
        # normal execution
        self.assertEqual(5, handler.handle(['0']))
        self.assertEqual([5, 6, 7], handler.handle(['*']))
        self.assertEqual("[5, 6, 7]", handler.handle(['+']))
        self.assertEqual(3, handler.handle(['count']))

        # exceptions
        self.assertRaises(Exception, handler.handle, [''])
        self.assertRaises(Exception, handler.handle, ['3'])
        self.assertRaises(Exception, handler.handle, ['/'])
        self.assertRaises(Exception, handler.handle, ['*/'])
        self.assertRaises(Exception, handler.handle, ['/*'])
        self.assertRaises(Exception, handler.handle, ['blabla'])
        self.assertRaises(Exception, handler.handle, ['bla', 'bla'])
        self.assertRaises(Exception, handler.handle, ['bla/'])
        self.assertRaises(Exception, handler.handle, ['', 'bla'])
        return

    def test_IndexCommandHandler(self) -> None:
        handler = IndexCommandHandler('pids')
        # normal execution
        psutil_val = handler.get_value()
        self.assertIsInstance(psutil_val, list)

        val1 = handler.handle(['*'])
        self.assertIsInstance(val1, list)

        val2 = handler.handle(['count'])
        assert isinstance(psutil_val, list)
        self.assertEqual(val2, len(psutil_val))

        val3 = handler.handle(['1'])
        self.assertEqual(val3, psutil_val[1])
        return

    def test_tuple_command_handler(self) -> None:
        test = namedtuple('test', 'a b')
        handler = type(
            "TestHandler",
            (TupleCommandHandler, object),
            {
                "get_value": lambda s: test(10, 20)
            })('test')
        # normal execution
        self.assertEqual(10, handler.handle(['a']))
        self.assertEqual({'a': 10, 'b': 20}, handler.handle(['*']))
        self.assertEqual('{"a": 10, "b": 20}', handler.handle(['+']))
        # exceptions
        self.assertRaises(Exception, handler.handle, [])
        self.assertRaises(Exception, handler.handle, [''])
        self.assertRaises(Exception, handler.handle, ['', '*'])
        self.assertRaises(Exception, handler.handle, ['blabla'])
        self.assertRaises(Exception, handler.handle, ['bla', 'bla'])
        self.assertRaises(Exception, handler.handle, ['bla/'])
        self.assertRaises(Exception, handler.handle, ['', 'bla'])

    def test_TupleCommandHandler(self) -> None:
        for foo in ('cpu_times', 'cpu_stats', 'virtual_memory', 'swap_memory'):
            handler = TupleCommandHandler(foo)
            val = handler.get_value()
            #print(val)
            self.assertIsInstance(val, tuple)

        # note that "sensors_battery" is not available on all platforms, so we accept
        # None as return value of get_value() for "sensors_battery"
        for foo_opt in ('sensors_battery'):
            handler = TupleCommandHandler(foo)
            val = handler.get_value()
            #print(val)
            if val is None:
                pass
            else:
                self.assertIsInstance(val, tuple)
        return

    def test_index_tuple_command_handler(self) -> None:
        test = namedtuple('test', 'a b')
        r = [
            test(1, 2),
            test(3, 4)
        ]
        handler = type(
            "TestHandler",
            (IndexTupleCommandHandler, object),
            {"get_value": lambda s: r})('test')
        # normal execution
        self.assertEqual([1, 3], handler.handle(['a', '*']))
        self.assertEqual("[1, 3]", handler.handle(['a', '+']))
        self.assertEqual(3, handler.handle(['a', '1']))
        self.assertEqual({'a': 3, 'b': 4}, handler.handle(['*', '1']))
        self.assertEqual('{"a": 3, "b": 4}', handler.handle(['+', '1']))
        # exceptions
        self.assertRaises(Exception, handler.handle, [''])
        self.assertRaises(Exception, handler.handle, ['*'])
        self.assertRaises(Exception, handler.handle, ['+'])
        self.assertRaises(Exception, handler.handle, ['a'])
        self.assertRaises(Exception, handler.handle, ['a', ''])
        self.assertRaises(Exception, handler.handle, ['*', ''])
        self.assertRaises(Exception, handler.handle, ['', '*'])
        self.assertRaises(Exception, handler.handle, ['blabla'])
        self.assertRaises(Exception, handler.handle, ['bla', 'bla'])
        self.assertRaises(Exception, handler.handle, ['bla/'])
        self.assertRaises(Exception, handler.handle, ['', 'bla'])

    def test_index_or_total_command_handler(self) -> None:
        handler = type("TestHandler", (IndexOrTotalCommandHandler, object),
                       {"get_value": lambda s, t: 5 if t else [1, 2, 3]})('test')
        # normal execution
        self.assertEqual(5, handler.handle(['']))
        self.assertEqual(1, handler.handle(['0']))
        self.assertEqual(3, handler.handle(['2']))
        self.assertEqual([1, 2, 3], handler.handle(['*']))
        self.assertEqual("[1, 2, 3]", handler.handle(['+']))
        self.assertEqual(3, handler.handle(['count']))
        # exceptions
        self.assertRaises(Exception, handler.handle, ['*-'])
        self.assertRaises(Exception, handler.handle, ['*', ''])
        self.assertRaises(Exception, handler.handle, ['', '*'])
        self.assertRaises(Exception, handler.handle, '3')
        self.assertRaises(Exception, handler.handle, ['blabla'])
        self.assertRaises(Exception, handler.handle, ['bla', 'bla'])
        self.assertRaises(Exception, handler.handle, ['bla/'])
        self.assertRaises(Exception, handler.handle, ['', 'bla'])

    def test_index_or_total_tuple_command_handler(self) -> None:
        test = namedtuple('test', 'a b')
        total = test(10, 20)
        single = [test(1, 2), test(3, 4)]
        handler = type("TestHandler", (IndexOrTotalTupleCommandHandler, object),
                       {"get_value": lambda s, t: total if t else single})('test')
        # normal execution
        self.assertEqual({'a': 10, 'b': 20}, handler.handle(['*']))
        self.assertEqual('{"a": 10, "b": 20}', handler.handle(['+']))
        self.assertEqual(10, handler.handle(['a']))
        self.assertEqual([1, 3], handler.handle(['a', '*']))
        self.assertEqual("[1, 3]", handler.handle(['a','+']))
        self.assertEqual(3, handler.handle(['a','1']))
        self.assertEqual({'a': 3, 'b': 4}, handler.handle(['*','1']))
        self.assertEqual('{"a": 3, "b": 4}', handler.handle(['+','1']))
        # exceptions
        #self.assertRaisesRegex(Exception, "Element '' in '' is not supported", handler.handle, '')
        self.assertRaisesRegex(Exception, "Cannot list all elements and parameters at the same.*", handler.handle, ['*','*'])
        self.assertRaises(Exception, handler.handle, ['*-'])
        self.assertRaises(Exception, handler.handle, ['','*'])
        self.assertRaises(Exception, handler.handle, ['3'])
        self.assertRaises(Exception, handler.handle, ['','3'])
        self.assertRaises(Exception, handler.handle, ['blabla'])
        self.assertRaises(Exception, handler.handle, ['bla', 'bla'])
        self.assertRaises(Exception, handler.handle, ['bla/'])
        self.assertRaises(Exception, handler.handle, ['', 'bla'])
        self.assertRaises(Exception, handler.handle, ['*','5'])

    def test_name_or_total_tuple_command_handler(self) -> None:
        test = namedtuple('test', 'a b')
        total = test(10, 20)
        single = {
            "x":  test(1, 2),
            "y": test(3, 4)
        }
        handler = type(
            "TestHandler",
            (NameOrTotalTupleCommandHandler, object),
            {"get_value": lambda s, t: total if t else single})('test')
        # normal execution
        self.assertEqual({'a': 10, 'b': 20}, handler.handle(['*']))
        self.assertEqual('{"a": 10, "b": 20}', handler.handle(['+']))
        self.assertEqual(10, handler.handle(['a']))
        self.assertEqual({"x": 1, "y": 3}, handler.handle(['a','*']))
        self.assertEqual('{"x": 1, "y": 3}', handler.handle(['a','+']))
        self.assertEqual(3, handler.handle(['a','y']))
        self.assertEqual({'a': 3, 'b': 4}, handler.handle(['*','y']))
        self.assertEqual('{"a": 3, "b": 4}', handler.handle(['+','y']))
        # exceptions
        self.assertRaisesRegex(Exception, "Element '' in .* is not supported", handler.handle, [''])
        self.assertRaisesRegex(Exception, "Cannot list all elements and parameters at the same.*", handler.handle, ['*','*'])
        self.assertRaises(Exception, handler.handle, ['*-'])
        self.assertRaises(Exception, handler.handle, ['','*'])
        self.assertRaises(Exception, handler.handle, ['3'])
        self.assertRaises(Exception, handler.handle, ['','3'])
        self.assertRaises(Exception, handler.handle, ['a','0'])
        self.assertRaises(Exception, handler.handle, ['c','x'])
        self.assertRaises(Exception, handler.handle, ['blabla'])
        self.assertRaises(Exception, handler.handle, ['bla', 'bla'])
        self.assertRaises(Exception, handler.handle, ['bla/'])
        self.assertRaises(Exception, handler.handle, ['', 'bla'])
        self.assertRaises(Exception, handler.handle, ['*','5'])
