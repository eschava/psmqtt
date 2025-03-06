# Copyright (c) 2016 psmqtt project
# Licensed under the MIT License.  See LICENSE file in the project root for full license information.

import fnmatch
import logging
import psutil
import re
from typing import (
    Any,
    Callable,
    Dict,
    List,
)

from .handlers_base import BaseHandler, Payload
from .utils import string_from_dict_optionally, string_from_list_optionally
from .handlers_base import TaskParam

class ProcessesCommandHandler(BaseHandler):
    '''
    This is the handler linking the Task class to the family of the
    ProcessCommandHandler-derived classes.
    This class is in charge of using psutil.process_iter() function
     (https://psutil.readthedocs.io/en/latest/#psutil.process_iter)
    to iterate over all running processes and extract the information
    selected via the usual parameters provided to the handle() method.
    '''

    top_cpu_regexp = re.compile(r"^top_cpu(\[\d+\])*$")
    top_memory_regexp = re.compile(r"^top_memory(\[\d+\])*$")
    top_number_regexp = re.compile(r"^top_[a-z_]+\[(\d+)\]$")
    pid_file_regexp = re.compile(r"^pid\[(.*)\]$")
    name_pattern_regexp = re.compile(r"^name\[(.*)\]$")

    def __init__(self) -> None:
        super().__init__('processes')
        return

    def handle(self, params:list[str], caller_task_id: str) -> Payload:
        assert isinstance(params, list)

        if len(params) != 2 and len(params) != 3:
            raise Exception(f"Exactly 2 or 3 parameters are supported for '{self.name}'; found {len(params)} parameters instead: {params}")
        process_id = params[0]
        property = params[1]
        remaining_params = [params[2]] if len(params) == 3 else []

        if TaskParam.is_wildcard(process_id):
            if TaskParam.is_regular_wildcard(property):
                raise Exception(f"The process property in '{self.name}' should be specified")
            result = {p.pid: self.get_process_value(p, property, remaining_params) for p in psutil.process_iter()}
            return string_from_dict_optionally(result, process_id.endswith(';'))
        elif isinstance(process_id, int):
            pid = process_id
        elif process_id.isdigit():
            pid = int(process_id)
        elif self.top_cpu_regexp.match(process_id):
            pid = self.find_process(process_id, lambda p: p.cpu_percent(), True)
        elif self.top_memory_regexp.match(process_id):
            pid = self.find_process(process_id, lambda p: p.memory_percent(), True)
        elif self.pid_file_regexp.match(process_id):
            m = self.pid_file_regexp.match(process_id)
            assert m is not None
            pid = self.get_pid_from_file(m.group(1).replace('|', '/'))
        elif self.name_pattern_regexp.match(process_id):
            m = self.name_pattern_regexp.match(process_id)
            assert m is not None
            pid = self.get_find_process(m.group(1))
        else:
            raise Exception("Process in '{self.name}' should be selected")

        if pid < 0:
            raise Exception(f"Process {process_id} not found")

        # we have a PID and property to fetch:
        return self.get_process_value(psutil.Process(pid), property, remaining_params)

    def find_process(self, request:str, cmp_func:Callable[..., float],
            reverse:bool) -> int:
        procs:List[psutil.Process] = []
        for p in psutil.process_iter():
            # do we just set a new attribute on a built-in object?
            p._sort_value = cmp_func(p)
            procs.append(p)

        procs = sorted(procs, key=lambda p: p._sort_value, reverse=reverse)
        m = self.top_number_regexp.match(request)
        index = 0 if m is None else int(m.group(1))
        return procs[index].pid

    @staticmethod
    def get_pid_from_file(filename:str) -> int:
        with open(filename) as f:
            return int(f.read())

    @staticmethod
    def get_find_process(pattern:str) -> int:
        for p in psutil.process_iter():
            if fnmatch.fnmatch(p.name(), pattern):
                return p.pid
        raise Exception("Process matching '" + pattern + "' not found")

    @staticmethod
    def get_process_value(process:psutil.Process, property:str, remaining_params:list[str]) -> Any:
        process_handler = process_handlers.get(property, None)
        if process_handler is None:
            raise Exception(f"Property '{property}' in 'processes' task is not supported")

        return process_handler.handle(remaining_params, process)

class ProcessCommandHandler:
    '''
    Base abstract class for all process-related command handlers.
    '''
    def __init__(self, name:str):
        self.name = name

    def handle(self, params: list[str], process:psutil.Process) -> Payload:
        assert isinstance(params, list)
        raise Exception("Not implemented")


class ProcessMethodCommandHandler(ProcessCommandHandler):
    '''
    This class implements the get_value() function by applying the psutil.Process.<METHOD>
    function to the process instance passed as a parameter to get_value(),
    where <METHOD> is actually the name of the class instance.
    '''
    def __init__(self, name:str):
        super().__init__(name)
        try:
            self.method = getattr(psutil.Process, self.name)
        except AttributeError:
            self.method = None  # method not defined
        return

    def handle(self, params: list[str], process:psutil.Process) -> Payload:
        assert isinstance(params, list)
        if params != []:
            raise Exception(f"Parameter '{params}' in '{self.name}' is not supported")

        return self.get_value(process)

    def get_value(self, process:psutil.Process) -> Payload:
        if self.method is None:
            raise Exception(f"Not implemented: psutil.{self.name}")
        # invoke the psutil method (e.g. "pid", "exe" etc) on the psutil.Process instance;
        # e.g.
        #     process = psutil.Process(1)
        #     method = getattr(psutil.Process, "exe")
        #     method(process)
        #   >> '/usr/lib/systemd/systemd'
        return self.method(process)


class ProcessPropertiesCommandHandler(ProcessCommandHandler):
    '''
    '''

    def __init__(self, name:str, join:bool, subproperties:bool):
        super().__init__(name)
        self.join = join
        self.subproperties = subproperties
        return

    def handle(self, params: list[str],process:psutil.Process) -> Payload:
        assert isinstance(params, list)
        if params != []:
            raise Exception("Parameter '" + params + "' in '" + self.name + "' is not supported")

        return self.get_value(process)

    def get_value(self, process:psutil.Process) -> Payload:
        result: Dict[str, Any] = dict()
        for k, handler in process_handlers.items():
            if hasattr(handler, "method") and handler.method is not None:  # property is defined for current OS
                try:
                    if isinstance(handler, ProcessMethodCommandHandler):
                        v = handler.handle('', process)
                        self.add_to_dict(result, k, v)
                    elif self.subproperties:
                        if isinstance(handler, ProcessMethodIndexCommandHandler) \
                                or isinstance(handler, ProcessMethodTupleCommandHandler):
                            v = handler.handle('*', process)
                            self.add_to_dict(result, k, v)
                except psutil.AccessDenied:  # just skip with property
                    logging.warning(f"AccessDenied when calling {handler}.handle()")

        return string_from_dict_optionally(result, self.join)

    def add_to_dict(self, d:Dict[str, Any], key:str, val:Any) -> None:
        '''
        Join or merge d and val
        '''
        if self.join:
            assert isinstance(d, dict)
            d[key] = val
        elif isinstance(val, dict):
            for k, v in val.items():
                d[key + "/" + k] = v
        elif isinstance(val, list):
            for i, v in enumerate(val):
                d[f"{key}/{i}"] = v
        else:
            d[key] = val
        return


class ProcessMethodIndexCommandHandler(ProcessMethodCommandHandler):

    def handle(self, params: list[str], process:psutil.Process) -> Payload:
        assert isinstance(params, list)
        if len(params) != 1:
            raise Exception(f"Exactly 1 parameter is supported for '{self.name}'; found {len(params)} parameters instead: {params}")
        param = params[0]

        assert self.method is not None
        arr = self.method(process)

        if TaskParam.is_wildcard(param):
            return string_from_list_optionally(arr, param.endswith(';'))
        elif param == 'count':
            return len(arr)
        elif isinstance(param, int):
            return arr[param]
        elif param.isdigit():
            return arr[int(param)]
        #else:
        raise Exception(f"Parameter '{param}' in '{self.name}' is not supported")


class ProcessMethodTupleCommandHandler(ProcessMethodCommandHandler):

    def handle(self, params: list[str], process:psutil.Process) -> Payload:
        assert isinstance(params, list)
        if len(params) != 1:
            raise Exception(f"Exactly 1 parameter is supported for '{self.name}'; found {len(params)} parameters instead: {params}")

        assert self.method is not None
        tup = self.method(process)

        param = params[0]
        if TaskParam.is_wildcard(param):
            return string_from_dict_optionally(tup._asdict(), param.endswith(';'))
        elif param in tup._fields:
            return getattr(tup, param)
        #else:
        raise Exception(f"Parameter '{param}' in '{self.name}' is not supported")


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
