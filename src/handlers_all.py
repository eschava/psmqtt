# Copyright (c) 2016 psmqtt project
# Licensed under the MIT License.  See LICENSE file in the project root for full license information.

import logging
import psutil
from typing import (
    List,
)

from .formatter import Formatter

from .handlers_base import Payload, TupleCommandHandler, ValueCommandHandler, IndexCommandHandler, IndexOrTotalCommandHandler, IndexTupleCommandHandler, IndexOrTotalTupleCommandHandler, NameOrTotalTupleCommandHandler
from .handlers_psutil_processes import ProcessesCommandHandler, ProcessPropertiesCommandHandler, ProcessMethodCommandHandler, ProcessMethodIndexCommandHandler, ProcessMethodTupleCommandHandler
from .handlers_psutil import DiskUsageCommandHandler, SensorsFansCommandHandler, DiskIOCountersCommandHandler, DiskIOCountersRateHandler, SensorsTemperaturesCommandHandler
from .handlers_pysmart import SmartCommandHandler

class TaskHandlers:

    handlers = {

        # CPU

        'cpu_times': TupleCommandHandler('cpu_times'),

        'cpu_percent': type(
            "CpuPercentCommandHandler",
            (IndexOrTotalCommandHandler, object),
            {
                "get_value": lambda self, total:
                    psutil.cpu_percent(percpu=not total)
            })('cpu_percent'),

        'cpu_times_percent': type(
            "CpuTimesPercentCommandHandler",
            (IndexOrTotalTupleCommandHandler, object),
            {
                "get_value": lambda self, total:
                    psutil.cpu_times_percent(percpu=not total)
            })('cpu_times_percent'),

        'cpu_stats': TupleCommandHandler('cpu_stats'),

        # MEMORY

        'virtual_memory': TupleCommandHandler('virtual_memory'),
        'swap_memory': TupleCommandHandler('swap_memory'),

        # DISK

        'disk_partitions': IndexTupleCommandHandler('disk_partitions'),
        'disk_usage': DiskUsageCommandHandler(),
        'disk_io_counters': DiskIOCountersCommandHandler(),
        'disk_io_counters_rate': DiskIOCountersRateHandler(),
        'smart': SmartCommandHandler(),

        # NETWORK

        'net_io_counters': type(
            "NetIOCountersCommandHandler",
            (NameOrTotalTupleCommandHandler, object),
            {
                "get_value": lambda self, total:
                    psutil.net_io_counters(pernic=not total)
            })('net_io_counters'),

        # PROCESSES

        'processes': ProcessesCommandHandler(),

        # OTHERS

        'users': IndexTupleCommandHandler('users'),
        'boot_time': ValueCommandHandler('boot_time'),
        'pids': IndexCommandHandler('pids'),

        # SENSORS

        'sensors_temperatures': SensorsTemperaturesCommandHandler(),
        'sensors_fans': SensorsFansCommandHandler(),
        'sensors_battery': TupleCommandHandler('sensors_battery'),
    }

    process_handlers = {
        '*': ProcessPropertiesCommandHandler('*', False, False),
        '**': ProcessPropertiesCommandHandler('**', False, True),
        '*;': ProcessPropertiesCommandHandler('*;', True, False),
        '**;': ProcessPropertiesCommandHandler('**;', True, True),
        'pid': type("ProcessPidCommandHandler", (ProcessMethodCommandHandler, object),
                    {"get_value": lambda self, process: process.pid})('pid'),
        'ppid': ProcessMethodCommandHandler('ppid'),
        'name': ProcessMethodCommandHandler('name'),
        'exe': ProcessMethodCommandHandler('exe'),
        'cwd': ProcessMethodCommandHandler('cwd'),
        'cmdline': ProcessMethodIndexCommandHandler('cmdline'),
        'status': ProcessMethodCommandHandler('status'),
        'username': ProcessMethodCommandHandler('username'),
        'create_time': ProcessMethodCommandHandler('create_time'),
        'terminal': ProcessMethodCommandHandler('terminal'),
        'uids': ProcessMethodTupleCommandHandler('uids'),
        'gids': ProcessMethodTupleCommandHandler('gids'),
        'cpu_times': ProcessMethodTupleCommandHandler('cpu_times'),
        'cpu_percent': ProcessMethodCommandHandler('cpu_percent'),
        'cpu_affinity': ProcessMethodIndexCommandHandler('cpu_affinity'),
        'memory_percent': ProcessMethodCommandHandler('memory_percent'),
        'memory_info': ProcessMethodTupleCommandHandler('memory_info'),
        'memory_full_info': ProcessMethodTupleCommandHandler('memory_full_info'),
        'io_counters': ProcessMethodTupleCommandHandler('io_counters'),
        'num_threads': ProcessMethodCommandHandler('num_threads'),
        'num_fds': ProcessMethodCommandHandler('num_fds'),
        'num_ctx_switches': ProcessMethodTupleCommandHandler('num_ctx_switches'),
        'nice': ProcessMethodCommandHandler('nice'),
    }

    @staticmethod
    def get_value(handlerName: str, params: list[str], formatter: str) -> Payload:
        '''
        Invokes the handler identified by the provided 'handlerName' with the given 'params';
        the handle will retrieves the sensor value(s), filter them and returns it/them.

        Then this function formats the output(s) invoking the 'formatter'.

        This is the main API for TaskHandlers.
        '''
        if handlerName not in TaskHandlers.handlers:
            raise Exception(f"Task '{handlerName}' is not supported")

        # invoke the handler to read the sensor values
        handler = TaskHandlers.handlers[handlerName]
        value = handler.handle(params)

        # if we get here, the reading was successful
        if logging.getLogger().isEnabledFor(logging.DEBUG):
            is_seq = isinstance(value, list) or isinstance(value, dict)
            desc = f"multiple results ({len(value)})" if is_seq else "single result"
            logging.debug(f"TaskHandlers.get_value(task '{handlerName}' with params {params}) produced {desc}:\n{value}")

        if formatter is not None:
            value = Formatter.format(formatter, value)
            logging.debug(f"TaskHandlers.get_value(task '{handlerName}' with params {params}) AFTER FORMATTING with {formatter} => {value}")

        # the value must be one of the types declared inside "Payload"
        assert isinstance(value, str) or isinstance(value, int) or isinstance(value, float) or isinstance(value, list) or isinstance(value, dict) or isinstance(value, tuple)

        return value

    @staticmethod
    def get_supported_handlers() -> List[str]:
        '''
        Returns list of supported handlers
        '''
        return list(TaskHandlers.handlers.keys())
