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
    SensorsFansCommandHandler
)

@pytest.mark.unit
class TestHandlers(unittest.TestCase):

    def test_disk_usage_command_handler(self) -> None:
        disk: Optional[str] = '/'
        handler = type("TestHandler", (DiskUsageCommandHandler, object),
                       {"get_value": lambda s,d: self._disk_usage_get_value(disk, d)})()
        # normal execution
        self.assertEqual(10, handler.handle(['a', '/']))
        self.assertEqual({'a': 10, 'b': 20}, handler.handle(['*', '/']))
        self.assertEqual('{"a": 10, "b": 20}', handler.handle(['+', '/']))
        self.assertEqual('{"a": 10, "b": 20}', handler.handle(['+', '/']))
        disk = 'c:'
        self.assertEqual(10, handler.handle(['a','c:']))
        disk = 'c:/'
        self.assertEqual(10, handler.handle(['a','c:/']))
        # exceptions
        disk = None     # do not validate disk, only parameters
        self.assertRaises(Exception, handler.handle, ['a'])
        self.assertRaises(Exception, handler.handle, ['a',''])
        self.assertRaises(Exception, handler.handle, ['/'])
        self.assertRaises(Exception, handler.handle, ['*',''])
        self.assertRaises(Exception, handler.handle, ['','*'])
        self.assertRaises(Exception, handler.handle, ['blabla'])
        self.assertRaises(Exception, handler.handle, ['bla', 'bla'])
        self.assertRaises(Exception, handler.handle, ['bla/'])
        self.assertRaises(Exception, handler.handle, ['', 'bla'])

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
        self.assertEqual(handler.handle(['*']), {"asus": [30.0], "coretemp": [45.0, 52.0]})
        self.assertEqual(handler.handle(['+']), '{"asus": [30.0], "coretemp": [45.0, 52.0]}')
        self.assertEqual(handler.handle(['asus']), [30.0])
        self.assertEqual(handler.handle(['asus','*']), [{"label": "", "current": 30.0, "high": None, "critical": None}])
        self.assertEqual(handler.handle(['asus','+']), '[{"critical": null, "current": 30.0, "high": null, "label": ""}]')
        self.assertEqual(handler.handle(['asus','','*']), {'label': '', 'current': 30.0, 'high': None, 'critical': None})
        self.assertEqual(handler.handle(['asus','','+']), '{"critical": null, "current": 30.0, "high": null, "label": ""}')
        self.assertEqual(handler.handle(['asus','','current']), 30.0)
        self.assertEqual(handler.handle(['asus',0]), 30.0)
        self.assertEqual(handler.handle(['asus',0,'*']), {'label': '', 'current': 30.0, 'high': None, 'critical': None})
        self.assertEqual(handler.handle(['asus',0,'+']), '{"critical": null, "current": 30.0, "high": null, "label": ""}')
        self.assertEqual(handler.handle(['asus',0,'current']), 30.0)
        self.assertEqual(handler.handle(['coretemp']), [45.0, 52.0])
        self.assertEqual(handler.handle(['coretemp','Core 0']), 45.0)
        self.assertEqual(handler.handle(['coretemp','Core 0','*']), {'label': 'Core 0', 'current': 45.0, 'high': 100.0, 'critical': 100.0})
        self.assertEqual(handler.handle(['coretemp','Core 0','+']), '{"critical": 100.0, "current": 45.0, "high": 100.0, "label": "Core 0"}')
        self.assertEqual(handler.handle(['coretemp','Core 0','current']), 45.0)

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
