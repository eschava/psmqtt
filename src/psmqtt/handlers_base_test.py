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

fake_task_id = "0.0"

@pytest.mark.unit
class TestHandlers(unittest.TestCase):

    def test_MockedValueCommandHandler(self) -> None:
        handler = type(
            "TestHandler",
            (ValueCommandHandler, object),
            {"get_value": lambda s: 50})('test')
        # normal execution
        self.assertEqual(50, handler.handle([], fake_task_id))
        # exceptions: ValueCommandHandler does not accept any parameters
        self.assertRaises(Exception, handler.handle, ['a'], fake_task_id)
        self.assertRaises(Exception, handler.handle, ['/'], fake_task_id)
        self.assertRaises(Exception, handler.handle, ['*'], fake_task_id)

    def test_ValueCommandHandler(self) -> None:
        handler = ValueCommandHandler("cpu_percent")
        # normal execution
        val = handler.handle([], fake_task_id)
        self.assertIsInstance(val, float)
        # exceptions: ValueCommandHandler does not accept any parameters
        self.assertRaises(Exception, handler.handle, ['a'], fake_task_id)

        return

    def test_MockedIndexCommandHandler(self) -> None:
        handler = type(
            "TestHandler",
            (IndexCommandHandler, object),
            {"get_value": lambda s: [5, 6, 7]})('test')
        # normal execution
        self.assertEqual(5, handler.handle(['0'], fake_task_id))
        self.assertEqual(6, handler.handle(['1'], fake_task_id))
        self.assertEqual(7, handler.handle(['2'], fake_task_id))
        self.assertEqual([5, 6, 7], handler.handle(['*'], fake_task_id))
        self.assertEqual("[5, 6, 7]", handler.handle(['+'], fake_task_id))
        self.assertEqual(3, handler.handle(['count'], fake_task_id))

        # exceptions: IndexCommandHandler wants a single parameter of type int (or string that can be converted to int)
        self.assertRaises(Exception, handler.handle, [''], fake_task_id)
        self.assertRaises(Exception, handler.handle, ['3'], fake_task_id)  # 3 is outside range
        self.assertRaises(Exception, handler.handle, ['/'], fake_task_id)
        self.assertRaises(Exception, handler.handle, ['*/'], fake_task_id)
        self.assertRaises(Exception, handler.handle, ['/*'], fake_task_id)
        self.assertRaises(Exception, handler.handle, ['blabla'], fake_task_id)
        self.assertRaises(Exception, handler.handle, ['bla', 'bla'], fake_task_id)
        self.assertRaises(Exception, handler.handle, ['bla/'], fake_task_id)
        self.assertRaises(Exception, handler.handle, ['', 'bla'], fake_task_id)
        return

    def test_IndexCommandHandler(self) -> None:
        handler = IndexCommandHandler('pids')
        # normal execution
        psutil_val = handler.get_value()
        self.assertIsInstance(psutil_val, list)

        val1 = handler.handle(['*'], fake_task_id)
        self.assertIsInstance(val1, list)

        val2 = handler.handle(['count'], fake_task_id)
        assert isinstance(psutil_val, list)
        self.assertEqual(val2, len(psutil_val))

        val3 = handler.handle(['1'], fake_task_id)
        self.assertEqual(val3, psutil_val[1])
        return

    def test_MockedTupleCommandHandler(self) -> None:
        testTuple = namedtuple('test', 'a b')
        handler = type(
            "TestHandler",
            (TupleCommandHandler, object),
            {
                "get_value": lambda s: testTuple(10, 20)
            })('test')
        # normal execution
        self.assertEqual(10, handler.handle(['a'], fake_task_id))
        self.assertEqual({'a': 10, 'b': 20}, handler.handle(['*'], fake_task_id))
        self.assertEqual('{"a": 10, "b": 20}', handler.handle(['+'], fake_task_id))
        # exceptions: TupleCommandHandler wants a single parameter of type string representing the name
        # of one of the fields of the namedtuple returned by get_value()
        self.assertRaises(Exception, handler.handle, [], fake_task_id)
        self.assertRaises(Exception, handler.handle, [''], fake_task_id)
        self.assertRaises(Exception, handler.handle, ['', '*'], fake_task_id)
        self.assertRaises(Exception, handler.handle, ['blabla'], fake_task_id)
        self.assertRaises(Exception, handler.handle, ['bla', 'bla'], fake_task_id)
        self.assertRaises(Exception, handler.handle, ['bla/'], fake_task_id)
        self.assertRaises(Exception, handler.handle, ['', 'bla'], fake_task_id)

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

    def test_MockedIndexTupleCommandHandler(self) -> None:
        test = namedtuple('test', 'a b')
        listOfTestTuples = [
            test(1, 2),
            test(3, 4)
        ]
        handler = type(
            "TestHandler",
            (IndexTupleCommandHandler, object),
            {"get_value": lambda s: listOfTestTuples})('test')
        # normal execution
        self.assertEqual([1, 3], handler.handle(['a', '*'], fake_task_id))
        self.assertEqual("[1, 3]", handler.handle(['a', '+'], fake_task_id))
        self.assertEqual(3, handler.handle(['a', '1'], fake_task_id))
        self.assertEqual({'a': 3, 'b': 4}, handler.handle(['*', '1'], fake_task_id))
        self.assertEqual('{"a": 3, "b": 4}', handler.handle(['+', '1'], fake_task_id))
        # exceptions: IndexTupleCommandHandler wants as first parameter a valid field name of the namedtuple
        # and as second parameter a valid index within the list of tuples returned by get_value()
        self.assertRaises(Exception, handler.handle, [''], fake_task_id)
        self.assertRaises(Exception, handler.handle, ['*'], fake_task_id)
        self.assertRaises(Exception, handler.handle, ['+'], fake_task_id)
        self.assertRaises(Exception, handler.handle, ['a'], fake_task_id)
        self.assertRaises(Exception, handler.handle, ['a', ''], fake_task_id)
        self.assertRaises(Exception, handler.handle, ['*', ''], fake_task_id)
        self.assertRaises(Exception, handler.handle, ['', '*'], fake_task_id)
        self.assertRaises(Exception, handler.handle, ['blabla'], fake_task_id)
        self.assertRaises(Exception, handler.handle, ['bla', 'bla'], fake_task_id)
        self.assertRaises(Exception, handler.handle, ['bla/'], fake_task_id)
        self.assertRaises(Exception, handler.handle, ['', 'bla'], fake_task_id)

    def test_MockedIndexOrTotalCommandHandler(self) -> None:
        handler = type("TestHandler", (IndexOrTotalCommandHandler, object),
                       {"get_value": lambda s, total: 5 if total else [1, 2, 3]})('test')
        # normal execution
        self.assertEqual(5, handler.handle([''], fake_task_id))
        self.assertEqual(1, handler.handle(['0'], fake_task_id))
        self.assertEqual(3, handler.handle(['2'], fake_task_id))
        self.assertEqual([1, 2, 3], handler.handle(['*'], fake_task_id))
        self.assertEqual("[1, 2, 3]", handler.handle(['+'], fake_task_id))
        self.assertEqual(3, handler.handle(['count'], fake_task_id))
        # exceptions
        self.assertRaises(Exception, handler.handle, ['*-'], fake_task_id)
        self.assertRaises(Exception, handler.handle, ['*', ''], fake_task_id)
        self.assertRaises(Exception, handler.handle, ['', '*'], fake_task_id)
        self.assertRaises(Exception, handler.handle, '3')
        self.assertRaises(Exception, handler.handle, ['blabla'], fake_task_id)
        self.assertRaises(Exception, handler.handle, ['bla', 'bla'], fake_task_id)
        self.assertRaises(Exception, handler.handle, ['bla/'], fake_task_id)
        self.assertRaises(Exception, handler.handle, ['', 'bla'], fake_task_id)

    def test_MockedIndexOrTotalTupleCommandHandler(self) -> None:
        testTuple = namedtuple('test', 'a b')
        totalTuple = testTuple(10, 20)
        listTuple = [testTuple(1, 2), testTuple(3, 4)]
        handler = type("TestHandler", (IndexOrTotalTupleCommandHandler, object),
                       {"get_value": lambda s, total: totalTuple if total else listTuple})('test')
        # normal execution
        self.assertEqual({'a': 10, 'b': 20}, handler.handle(['*'], fake_task_id))
        self.assertEqual('{"a": 10, "b": 20}', handler.handle(['+'], fake_task_id))
        self.assertEqual(10, handler.handle(['a'], fake_task_id))
        self.assertEqual([1, 3], handler.handle(['a', '*'], fake_task_id))
        self.assertEqual("[1, 3]", handler.handle(['a','+'], fake_task_id))
        self.assertEqual(3, handler.handle(['a','1'], fake_task_id))
        self.assertEqual({'a': 3, 'b': 4}, handler.handle(['*','1'], fake_task_id))
        self.assertEqual('{"a": 3, "b": 4}', handler.handle(['+','1'], fake_task_id))
        # exceptions
        #self.assertRaisesRegex(Exception, "Element '' in '' is not supported", handler.handle, '')
        self.assertRaisesRegex(Exception, "Cannot list all elements and parameters at the same.*", handler.handle, ['*','*'], fake_task_id)
        self.assertRaises(Exception, handler.handle, ['*-'], fake_task_id)
        self.assertRaises(Exception, handler.handle, ['','*'], fake_task_id)
        self.assertRaises(Exception, handler.handle, ['3'], fake_task_id)
        self.assertRaises(Exception, handler.handle, ['','3'], fake_task_id)
        self.assertRaises(Exception, handler.handle, ['blabla'], fake_task_id)
        self.assertRaises(Exception, handler.handle, ['bla', 'bla'], fake_task_id)
        self.assertRaises(Exception, handler.handle, ['bla/'], fake_task_id)
        self.assertRaises(Exception, handler.handle, ['', 'bla'], fake_task_id)
        self.assertRaises(Exception, handler.handle, ['*','5'], fake_task_id)

    def test_MockedNameOrTotalTupleCommandHandler(self) -> None:
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
        self.assertEqual({'a': 10, 'b': 20}, handler.handle(['*'], fake_task_id))
        self.assertEqual('{"a": 10, "b": 20}', handler.handle(['+'], fake_task_id))
        self.assertEqual(10, handler.handle(['a'], fake_task_id))
        self.assertEqual({"x": 1, "y": 3}, handler.handle(['a','*'], fake_task_id))
        self.assertEqual('{"x": 1, "y": 3}', handler.handle(['a','+'], fake_task_id))
        self.assertEqual(3, handler.handle(['a','y'], fake_task_id))
        self.assertEqual({'a': 3, 'b': 4}, handler.handle(['*','y'], fake_task_id))
        self.assertEqual('{"a": 3, "b": 4}', handler.handle(['+','y'], fake_task_id))
        # exceptions
        self.assertRaisesRegex(Exception, "Element '' in .* is not supported", handler.handle, [''], fake_task_id)
        self.assertRaisesRegex(Exception, "Cannot list all elements and parameters at the same.*", handler.handle, ['*','*'], fake_task_id)
        self.assertRaises(Exception, handler.handle, ['*-'], fake_task_id)
        self.assertRaises(Exception, handler.handle, ['','*'], fake_task_id)
        self.assertRaises(Exception, handler.handle, ['3'], fake_task_id)
        self.assertRaises(Exception, handler.handle, ['','3'], fake_task_id)
        self.assertRaises(Exception, handler.handle, ['a','0'], fake_task_id)
        self.assertRaises(Exception, handler.handle, ['c','x'], fake_task_id)
        self.assertRaises(Exception, handler.handle, ['blabla'], fake_task_id)
        self.assertRaises(Exception, handler.handle, ['bla', 'bla'], fake_task_id)
        self.assertRaises(Exception, handler.handle, ['bla/'], fake_task_id)
        self.assertRaises(Exception, handler.handle, ['', 'bla'], fake_task_id)
        self.assertRaises(Exception, handler.handle, ['*','5'], fake_task_id)
