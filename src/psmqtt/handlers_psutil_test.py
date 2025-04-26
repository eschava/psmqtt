# Copyright (c) 2016 psmqtt project
# Licensed under the MIT License.  See LICENSE file in the project root for full license information.

import unittest
import collections
from collections import namedtuple
from typing import Any, Dict, NamedTuple, Optional
import psutil._common
import pytest

from .handlers_psutil import (
    DiskUsageCommandHandler,
    SensorsTemperaturesCommandHandler,
    SensorsFansCommandHandler,
    GetLoadAvgCommandHandler
)

fake_task_id = "0.0"

@pytest.mark.unit
class TestHandlers(unittest.TestCase):

    def test_MockedDiskUsageCommandHandler(self) -> None:
        disk: Optional[str] = '/'
        handler = type("TestHandler", (DiskUsageCommandHandler, object),
                       {"get_value": lambda s,d: self._disk_usage_get_value(disk, d)})()
        # normal execution: read field "a" from the fake tuple returned for disk "/"
        self.assertEqual(10, handler.handle(['a', '/'], fake_task_id))
        self.assertEqual({'a': 10, 'b': 20}, handler.handle(['*', '/'], fake_task_id))
        self.assertEqual('{"a": 10, "b": 20}', handler.handle(['+', '/'], fake_task_id))
        self.assertEqual('{"a": 10, "b": 20}', handler.handle(['+', '/'], fake_task_id))
        disk = 'c:'
        self.assertEqual(10, handler.handle(['a','c:'], fake_task_id))
        disk = 'c:/'
        self.assertEqual(10, handler.handle(['a','c:/'], fake_task_id))
        # exceptions
        disk = None     # do not validate disk, only parameters
        self.assertRaises(Exception, handler.handle, ['a'], fake_task_id)
        self.assertRaises(Exception, handler.handle, ['a',''], fake_task_id)
        self.assertRaises(Exception, handler.handle, ['/'], fake_task_id)
        self.assertRaises(Exception, handler.handle, ['*',''], fake_task_id)
        self.assertRaises(Exception, handler.handle, ['','*'], fake_task_id)
        self.assertRaises(Exception, handler.handle, ['blabla'], fake_task_id)
        self.assertRaises(Exception, handler.handle, ['bla', 'bla'], fake_task_id)
        self.assertRaises(Exception, handler.handle, ['bla/'], fake_task_id)
        self.assertRaises(Exception, handler.handle, ['', 'bla'], fake_task_id)

    def _disk_usage_get_value(self, disk: Optional[str], d:str) -> NamedTuple:
        if disk is not None:
            self.assertEqual(disk, d)
        test = namedtuple('test', 'a b')
        return test(10, 20)

    def test_DiskUsageCommandHandler(self) -> None:
        handler = DiskUsageCommandHandler()
        val = handler.get_value('/')
        self.assertIsInstance(val, tuple)
        return

    def test_MockedSensorsTemperaturesCommandHandler(self) -> None:
        handler = type(
            "TestHandler",
            (SensorsTemperaturesCommandHandler, object),
            {
                "get_value": lambda s: self._temperature_sensors_get_value()
            })()
        self.assertEqual(handler.handle(['*'], fake_task_id), {"asus": [30.0], "coretemp": [45.0, 52.0]})
        self.assertEqual(handler.handle(['+'], fake_task_id), '{"asus": [30.0], "coretemp": [45.0, 52.0]}')
        self.assertEqual(handler.handle(['asus'], fake_task_id), [30.0])
        self.assertEqual(handler.handle(['asus','*'], fake_task_id), [{"label": "", "current": 30.0, "high": None, "critical": None}])
        self.assertEqual(handler.handle(['asus','+'], fake_task_id), '[{"critical": null, "current": 30.0, "high": null, "label": ""}]')
        self.assertEqual(handler.handle(['asus','','*'], fake_task_id), {'label': '', 'current': 30.0, 'high': None, 'critical': None})
        self.assertEqual(handler.handle(['asus','','+'], fake_task_id), '{"critical": null, "current": 30.0, "high": null, "label": ""}')
        self.assertEqual(handler.handle(['asus','','current'], fake_task_id), 30.0)
        self.assertEqual(handler.handle(['asus',0], fake_task_id), 30.0)
        self.assertEqual(handler.handle(['asus',0,'*'], fake_task_id), {'label': '', 'current': 30.0, 'high': None, 'critical': None})
        self.assertEqual(handler.handle(['asus',0,'+'], fake_task_id), '{"critical": null, "current": 30.0, "high": null, "label": ""}')
        self.assertEqual(handler.handle(['asus',0,'current'], fake_task_id), 30.0)
        self.assertEqual(handler.handle(['coretemp'], fake_task_id), [45.0, 52.0])
        self.assertEqual(handler.handle(['coretemp','Core 0'], fake_task_id), 45.0)
        self.assertEqual(handler.handle(['coretemp','Core 0','*'], fake_task_id), {'label': 'Core 0', 'current': 45.0, 'high': 100.0, 'critical': 100.0})
        self.assertEqual(handler.handle(['coretemp','Core 0','+'], fake_task_id), '{"critical": 100.0, "current": 45.0, "high": 100.0, "label": "Core 0"}')
        self.assertEqual(handler.handle(['coretemp','Core 0','current'], fake_task_id), 45.0)

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

    def test_GetLoadAvgCommandHandler(self) -> None:
        handler = type("TestHandler", (GetLoadAvgCommandHandler, object),
                       {"get_value": lambda s: (2.5, 0.3, 0.1)})()
        val = handler.get_value()
        self.assertIsInstance(val, tuple)
        self.assertEqual(val, (2.5, 0.3, 0.1))

        num_cpu_cores = psutil.cpu_count()

        def abs2percent(abs_load_value) -> float:
            return 100 * abs_load_value / num_cpu_cores

        # normal execution: read pseudo-field "last1min"
        self.assertEqual(2.5, handler.handle(['last1min', 'abs'], fake_task_id))
        self.assertEqual(abs2percent(2.5), handler.handle(['last1min', 'percent'], fake_task_id))

        # normal execution: read pseudo-field "last5min"
        self.assertEqual(0.3, handler.handle(['last5min', 'abs'], fake_task_id))
        self.assertEqual(abs2percent(0.3), handler.handle(['last5min', 'percent'], fake_task_id))

        # normal execution: read pseudo-field "last15min"
        self.assertEqual(0.1, handler.handle(['last15min', 'abs'], fake_task_id))
        self.assertEqual(abs2percent(0.1), handler.handle(['last15min', 'percent'], fake_task_id))

        # exceptions
        self.assertRaises(Exception, handler.handle, ['whatever'], fake_task_id)
        self.assertRaises(Exception, handler.handle, ['last1min', 'wrongParam'], fake_task_id)
        self.assertRaises(Exception, handler.handle, ['last1min', 'percent', 'tooManyParams'], fake_task_id)
