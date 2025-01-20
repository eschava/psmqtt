import unittest
import collections
from collections import namedtuple
from typing import Any, Dict, NamedTuple, Optional
import psutil._common

from .handlers import (
    DiskUsageCommandHandler,
    IndexCommandHandler,
    IndexOrTotalCommandHandler,
    IndexOrTotalTupleCommandHandler,
    IndexTupleCommandHandler,
    NameOrTotalTupleCommandHandler,
    ProcessesCommandHandler,
    SensorsTemperaturesCommandHandler,
    SmartCommandHandler,
    TupleCommandHandler,
    SensorsFansCommandHandler,
    ValueCommandHandler,
    get_value
)

class TestHandlers(unittest.TestCase):

    def test_value_command_handler(self) -> None:
        handler = type(
            "TestHandler",
            (ValueCommandHandler, object),
            {"get_value": lambda s: 50})('test')
        # normal execution
        self.assertEqual(50, handler.handle(''))
        # exceptions
        self.assertRaises(Exception, handler.handle, 'a')
        self.assertRaises(Exception, handler.handle, '/')
        self.assertRaises(Exception, handler.handle, '*')

    def test_ValueCommandHandler(self) -> None:
        handler = ValueCommandHandler("cpu_percent")
        # normal execution
        val = handler.handle('')
        self.assertIsInstance(val, float)
        # exceptions
        self.assertRaises(Exception, handler.handle, 'a')

        return

    def test_index_command_handler(self) -> None:
        handler = type(
            "TestHandler",
            (IndexCommandHandler, object),
            {"get_value": lambda s: [5, 6, 7]})('test')
        # normal execution
        self.assertEqual(5, handler.handle('0'))
        self.assertEqual([5, 6, 7], handler.handle('*'))
        self.assertEqual("[5, 6, 7]", handler.handle('*;'))
        self.assertEqual(3, handler.handle('count'))

        # exceptions
        self.assertRaises(Exception, handler.handle, '')
        self.assertRaises(Exception, handler.handle, '3')
        self.assertRaises(Exception, handler.handle, '/')
        self.assertRaises(Exception, handler.handle, '*/')
        self.assertRaises(Exception, handler.handle, '/*')
        self.assertRaises(Exception, handler.handle, 'blabla')
        self.assertRaises(Exception, handler.handle, 'bla/bla')
        self.assertRaises(Exception, handler.handle, 'bla/')
        self.assertRaises(Exception, handler.handle, '/bla')
        return

    def test_IndexCommandHandler(self) -> None:
        handler = IndexCommandHandler('pids')
        # normal execution
        psutil_val = handler.get_value()
        self.assertIsInstance(psutil_val, list)

        val1 = handler.handle('*')
        self.assertIsInstance(val1, list)

        val2 = handler.handle('count')
        assert isinstance(psutil_val, list)
        self.assertEqual(val2, len(psutil_val))

        val3 = handler.handle('1')
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
        self.assertEqual(10, handler.handle('a'))
        self.assertEqual({'a': 10, 'b': 20}, handler.handle('*'))
        self.assertEqual('{"a": 10, "b": 20}', handler.handle('*;'))
        # exceptions
        self.assertRaises(Exception, handler.handle, '')
        self.assertRaises(Exception, handler.handle, '/')
        self.assertRaises(Exception, handler.handle, '*/')
        self.assertRaises(Exception, handler.handle, '/*')
        self.assertRaises(Exception, handler.handle, 'blabla')
        self.assertRaises(Exception, handler.handle, 'bla/bla')
        self.assertRaises(Exception, handler.handle, 'bla/')
        self.assertRaises(Exception, handler.handle, '/bla')

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
        self.assertEqual([1, 3], handler.handle('a/*'))
        self.assertEqual("[1, 3]", handler.handle('a/*;'))
        self.assertEqual(3, handler.handle('a/1'))
        self.assertEqual({'a': 3, 'b': 4}, handler.handle('*/1'))
        self.assertEqual('{"a": 3, "b": 4}', handler.handle('*;/1'))
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

    def test_index_or_total_command_handler(self) -> None:
        handler = type("TestHandler", (IndexOrTotalCommandHandler, object),
                       {"get_value": lambda s, t: 5 if t else [1, 2, 3]})('test')
        # normal execution
        self.assertEqual(5, handler.handle(''))
        self.assertEqual(1, handler.handle('0'))
        self.assertEqual(3, handler.handle('2'))
        self.assertEqual([1, 2, 3], handler.handle('*'))
        self.assertEqual("[1, 2, 3]", handler.handle('*;'))
        self.assertEqual(3, handler.handle('count'))
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

    def test_index_or_total_tuple_command_handler(self) -> None:
        test = namedtuple('test', 'a b')
        total = test(10, 20)
        single = [test(1, 2), test(3, 4)]
        handler = type("TestHandler", (IndexOrTotalTupleCommandHandler, object),
                       {"get_value": lambda s, t: total if t else single})('test')
        # normal execution
        self.assertEqual({'a': 10, 'b': 20}, handler.handle('*'))
        self.assertEqual('{"a": 10, "b": 20}', handler.handle('*;'))
        self.assertEqual(10, handler.handle('a'))
        self.assertEqual([1, 3], handler.handle('a/*'))
        self.assertEqual("[1, 3]", handler.handle('a/*;'))
        self.assertEqual(3, handler.handle('a/1'))
        self.assertEqual({'a': 3, 'b': 4}, handler.handle('*/1'))
        self.assertEqual('{"a": 3, "b": 4}', handler.handle('*;/1'))
        # exceptions
        self.assertRaisesRegex(Exception, "Element '' in '' is not supported", handler.handle, '')
        self.assertRaises(Exception, handler.handle, '/')
        self.assertRaisesRegex(Exception, "Cannot list all elements and parameters at the same.*", handler.handle, '*/*')
        self.assertRaises(Exception, handler.handle, '*-')
        self.assertRaises(Exception, handler.handle, '/*')
        self.assertRaises(Exception, handler.handle, '3')
        self.assertRaises(Exception, handler.handle, '/3')
        self.assertRaises(Exception, handler.handle, 'blabla')
        self.assertRaises(Exception, handler.handle, 'bla/bla')
        self.assertRaises(Exception, handler.handle, 'bla/')
        self.assertRaises(Exception, handler.handle, '/bla')
        self.assertRaises(Exception, handler.handle, '*/5')

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
        self.assertEqual({'a': 10, 'b': 20}, handler.handle('*'))
        self.assertEqual('{"a": 10, "b": 20}', handler.handle('*;'))
        self.assertEqual(10, handler.handle('a'))
        self.assertEqual({"x": 1, "y": 3}, handler.handle('a/*'))
        self.assertEqual('{"x": 1, "y": 3}', handler.handle('a/*;'))
        self.assertEqual(3, handler.handle('a/y'))
        self.assertEqual({'a': 3, 'b': 4}, handler.handle('*/y'))
        self.assertEqual('{"a": 3, "b": 4}', handler.handle('*;/y'))
        # exceptions
        self.assertRaisesRegex(Exception, "Element '' in '' is not supported", handler.handle, '')
        self.assertRaises(Exception, handler.handle, '/')
        self.assertRaisesRegex(Exception, "Cannot list all elements and parameters at the same.*", handler.handle, '*/*')
        self.assertRaises(Exception, handler.handle, '*-')
        self.assertRaises(Exception, handler.handle, '/*')
        self.assertRaises(Exception, handler.handle, '3')
        self.assertRaises(Exception, handler.handle, '/3')
        self.assertRaises(Exception, handler.handle, 'a/0')
        self.assertRaises(Exception, handler.handle, 'c/x')
        self.assertRaises(Exception, handler.handle, 'blabla')
        self.assertRaises(Exception, handler.handle, 'bla/bla')
        self.assertRaises(Exception, handler.handle, 'bla/')
        self.assertRaises(Exception, handler.handle, '/bla')
        self.assertRaises(Exception, handler.handle, '*/5')

    def test_disk_usage_command_handler(self) -> None:
        disk: Optional[str] = '/'
        handler = type("TestHandler", (DiskUsageCommandHandler, object),
                       {"get_value": lambda s,d: self._disk_usage_get_value(disk, d)})()
        # normal execution
        self.assertEqual(10, handler.handle('a//'))
        self.assertEqual({'a': 10, 'b': 20}, handler.handle('*//'))
        self.assertEqual('{"a": 10, "b": 20}', handler.handle('*;//'))
        self.assertEqual('{"a": 10, "b": 20}', handler.handle('*;/|'))  # vertical slash
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

    def _disk_usage_get_value(self, disk: Optional[str], d:str) -> NamedTuple:
        if disk is not None:
            self.assertEqual(disk, d)
        test = namedtuple('test', 'a b')
        return test(10, 20)

    def test_DiskUsageCommandHandler(self) -> None:
        handler = DiskUsageCommandHandler()
        val = handler.get_value('/')
        #print(val)
        self.assertIsInstance(val, tuple)
        return

    def test_temperature_sensors(self) -> None:
        handler = type(
            "TestHandler",
            (SensorsTemperaturesCommandHandler, object),
            {
                "get_value": lambda s: self._temperature_sensors_get_value()
            })()
        self.assertEqual(handler.handle('*'), {"asus": [30.0], "coretemp": [45.0, 52.0]})
        self.assertEqual(handler.handle('*;'), '{"asus": [30.0], "coretemp": [45.0, 52.0]}')
        self.assertEqual(handler.handle('asus'), [30.0])
        self.assertEqual(handler.handle('asus/*'), [{"label": "", "current": 30.0, "high": None, "critical": None}])
        self.assertEqual(handler.handle('asus/*;'), '[{"critical": null, "current": 30.0, "high": null, "label": ""}]')
        self.assertEqual(handler.handle('asus//*'), {'label': '', 'current': 30.0, 'high': None, 'critical': None})
        self.assertEqual(handler.handle('asus//*;'), '{"critical": null, "current": 30.0, "high": null, "label": ""}')
        self.assertEqual(handler.handle('asus//current'), 30.0)
        self.assertEqual(handler.handle('asus/0'), 30.0)
        self.assertEqual(handler.handle('asus/0/*'), {'label': '', 'current': 30.0, 'high': None, 'critical': None})
        self.assertEqual(handler.handle('asus/0/*;'), '{"critical": null, "current": 30.0, "high": null, "label": ""}')
        self.assertEqual(handler.handle('asus/0/current'), 30.0)
        self.assertEqual(handler.handle('coretemp'), [45.0, 52.0])
        self.assertEqual(handler.handle('coretemp/Core 0'), 45.0)
        self.assertEqual(handler.handle('coretemp/Core 0/*'), {'label': 'Core 0', 'current': 45.0, 'high': 100.0, 'critical': 100.0})
        self.assertEqual(handler.handle('coretemp/Core 0/*;'), '{"critical": 100.0, "current": 45.0, "high": 100.0, "label": "Core 0"}')
        self.assertEqual(handler.handle('coretemp/Core 0/current'), 45.0)

    @staticmethod
    def _temperature_sensors_get_value() -> Dict[str, Any]:
        ret = collections.defaultdict(list)
        ret['coretemp'].append(psutil._common.shwtemp('Core 0', 45.0, 100.0, 100.0))
        ret['coretemp'].append(psutil._common.shwtemp('Core 1', 52.0, 100.0, 100.0))
        ret['asus'].append(psutil._common.shwtemp('', 30.0, None, None))
        return dict(ret)

    def test_SensorsFansCommandHandler(self) -> None:
        handler = SensorsFansCommandHandler()
        val = handler.get_value()
        #print(val)
        self.assertIsInstance(val, dict)
        assert isinstance(val, dict)
        for k,v in val.items():
            self.assertIsInstance(k, str)
            self.assertIsInstance(v, list)
            for t in v:
                self.assertIsInstance(t, tuple)
        return

    def test_ProcessesCommandHandler(self) -> None:
        handler = ProcessesCommandHandler()
        processes = handler.handle('*/name')
        self.assertIsInstance(processes, dict)
        assert isinstance(processes, dict)
        self.assertGreater(len(processes), 3)
        last_pid = 0
        last_name = ''
        for k,v in processes.items():
            if not last_name:
                assert isinstance(k, int)
                last_pid = k
                last_name = v
            assert isinstance(k, int)
            assert isinstance(v, str)
            assert isinstance(k, int)

        res = handler.handle(f'{last_pid}/name')
        self.assertEqual(res, last_name)

        processes = handler.handle('top_cpu/name')
        self.assertIsInstance(processes, str)

        processes = handler.handle('top_memory/exe')
        self.assertIsInstance(processes, str)

        pid = handler.handle(f'name[{last_name}]/pid')
        self.assertEqual(pid, last_pid)
        return

    def test_get_value(self) -> None:
        val = get_value('cpu_percent')
        self.assertIsInstance(val, float)

        val = get_value('virtual_memory/percent')
        self.assertIsInstance(val, float)

        return

    def test_SmartCommandHandler(self) -> None:
        handler = SmartCommandHandler()
        #val = handler.get_value()
        try:
            val = handler.handle('dev/nvme0')
            #print(val)
            self.assertIsInstance(val, dict)
            assert isinstance(val, dict)

            self.assertEqual(
                handler.handle('*'), {"asus": [30.0], "coretemp": [45.0, 52.0]})
        except Exception:
            pass

        return


if __name__ == '__main__':
    unittest.main()
