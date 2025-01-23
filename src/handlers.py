#from collections import namedtuple
import fnmatch
import json
import logging
import psutil  # pip install psutil
from pySMART import Device as SmartDevice
import re
from typing import (
    Any,
    Callable,
    Dict,
    List,
    NamedTuple,
    Optional,
    Sized,
    Tuple,
    Union
)

from .formatter import Formatter

# all command handlers will return from their handle() function a Payload:
Payload = Union[List[Any], Dict[str, Any], NamedTuple, str, float, int]

class CommandHandler:
    '''
    Abstract base class that has a handle method
    '''

    def __init__(self, name:str):
        self.name = name
        return

    def handle(self, params: list[str]) -> Payload:
        '''
        Will call self.get_value()
        '''
        raise Exception("Not implemented")

    def get_value(self) -> Payload:
        raise Exception("Not implemented")

class MethodCommandHandler(CommandHandler):
    '''
    Abstract base class that has a handle method
    '''

    def __init__(self, name:str):
        super().__init__(name)
        #
        # on FreeBSD sensors_fans is not defined!
        #
        self.method: Optional[Callable[..., Payload]] = getattr(psutil, name, None)
        if self.method is None:
            logging.warning(f"psutil '{self.name}' not implemented")
        return

    def handle(self, params: list[str]) -> Payload:
        '''
        Will call self.get_value()
        '''
        raise Exception("Not implemented")

    def get_value(self) -> Payload:
        if self.method is None:
            raise Exception(f"psutil '{self.name}' not implemented")
        return self.method()

class ValueCommandHandler(MethodCommandHandler):
    '''
    CommandHandler with self.method pointing to psutil function,
    e.g. psutil.cpu_percent(), boot_time.
    handle invokes self.method and just returns its value.
    '''

    def handle(self, params: list[str]) -> Payload:
        if params != []:
            raise Exception(f"Parameter '{params}' in '{self.name}' is not supported")

        return self.get_value()

class IndexCommandHandler(MethodCommandHandler):
    '''
    CommandHandler with self.method pointing to psutil function returning a
    list, e.g. pids
    '''

    def handle(self, params: list[str]) -> Payload:
        arr = self.get_value()
        assert isinstance(arr, list)

        if len(params) > 1:
            raise Exception(f"Exactly 1 parameter is supported; found {len(params)} parameters instead: {params}")
        if len(params) == 0:
            raise Exception(f"Found 0 parameters, need exactly 1 in '{self.name}'")

        param = params[0]
        if param == '*' or param == '*;':
            return string_from_list_optionally(arr, param.endswith(';'))
        elif param == 'count':
            return len(arr)
        elif param.isdigit():
            return arr[int(param)]
        raise Exception(f"Parameter '{param}' in '{self.name}' is not supported")


class TupleCommandHandler(MethodCommandHandler):
    '''
    CommandHandler with self.method pointing to a psutil function returning a
    tuple, e.g. cpu_times, cpu_stats, virtual_memory, swap_memory
    '''

    def handle(self, params: list[str]) -> Payload:
        tup = self.get_value()
        assert isinstance(tup, tuple)

        if len(params) != 1:
            raise Exception(f"Exactly 1 parameter is supported for '{self.name}'; found {len(params)} parameters instead: {params}")

        # the parameter for this handler decides which tuple field we should select:
        tuple_field = params[0]
        if tuple_field == '*':
            return tup._asdict()
        if tuple_field == '*;':
            return string_from_dict(tup._asdict())
        elif tuple_field in tup._fields:
            return getattr(tup, tuple_field)
        elif tuple_field == '':
            raise Exception(f"Parameter in '{self.name}' should be selected")
        raise Exception(f"Parameter '{tuple_field}' in '{self.name}' is not supported")


class IndexTupleCommandHandler(MethodCommandHandler):
    '''
    CommandHandler with self.method pointing to a psutil function returning a
    list of named tuples, e.g. disk_partitions, users
    '''

    def handle(self, params: list[str]) -> Payload:
        if len(params) == 0:
            raise Exception(f"Found 0 parameters, need 1 or 2 in '{self.name}'")

        param = params[0]
        index_str = params[1] if len(params) >= 2 else ''

        all_params = param == '*' or param == '*;'
        index = -1

        if param.isdigit():
            all_params = True
            index = int(param)
        elif index_str.isdigit():
            index = int(index_str)
        elif index_str != '*' and index_str != '*;':
            raise Exception(f"Element '{index_str}' in '{params}' is not supported")

        if index < 0 and all_params:
            raise Exception(f"Cannot list all elements and parameters at the same '{params}' request")

        result = self.get_value()
        assert isinstance(result, list)
        if index < 0:
            return list_from_array_of_namedtupes(result, param, params, index_str.endswith(';'))
        else:  # index selected
            try:
                elt = result[index]
                if all_params:
                    return string_from_dict_optionally(elt._asdict(), param.endswith(';'))
                elif param in elt._fields:
                    return getattr(elt, param)
                else:
                    raise Exception("Parameter '" + param + "' in '" + params + "' is not supported")
            except IndexError:
                raise Exception("Element #" + str(index) + " is not present")

class IndexOrTotalCommandHandler(CommandHandler):
    '''
    CommandHandler with self.method pointing to a psutil function which
    returns a ??, e.g. psutils.cpu_percent.
    '''
    def __init__(self, name:str):
        super().__init__(name)
        return

    def handle(self, params: list[str]) -> Payload:
        total = True
        join = False
        count = False
        index = -1
        if len(params) != 0 and len(params) != 1:
            raise Exception(f"Exactly 0 or 1 parameters are supported for '{self.name}'; found {len(params)} parameters instead: {params}")

        param = params[0] if len(params) == 1 else ''

        if param == '*':
            total = False
        elif param == '*;':
            total = False
            join = True
        elif param == 'total':
            total = True
        elif param == 'count':
            total = False
            count = True
        elif param.isdigit():
            total = False
            index = int(param)
        elif param != '':
            raise Exception("Parameter '" + param + "' in '" + self.name + "' is not supported")

        try:
            result = self.get_value(total)
            assert isinstance(result, list) or isinstance(result, float) or isinstance(result, int)
            if count:
                assert isinstance(result, Sized)
                return len(result)
            elif index >= 0:
                assert isinstance(result, list)
                return result[index]
            elif isinstance(result, list):
                return string_from_list_optionally(result, join)
            else:
                return result
        except IndexError:
            raise Exception("Element #" + str(index) + " is not present")

    # noinspection PyMethodMayBeStatic
    def get_value(self, total:bool) -> List[Any]:
        '''
        cpu_percent is not using this
        '''
        raise Exception("Not implemented")


class IndexOrTotalTupleCommandHandler(MethodCommandHandler):
    '''
    used by, e.g. cpu_times_percent
    '''
    def __init__(self, name:str):
        super().__init__(name)

    def handle(self, params: list[str]) -> Payload:
        if len(params) != 1 and len(params) != 2:
            raise Exception(f"Exactly 1 or 2 parameters are supported for '{self.name}'; found {len(params)} parameters instead: {params}")

        param = params[0]
        index_str = params[1] if len(params) == 2 else ''

        all_params = param == '*' or param == '*;'
        params_join = param.endswith(';')

        total = True
        index_join = False
        index = -1
        if index_str == '*':
            total = False
        elif index_str == '*;':
            total = False
            index_join = True
        elif index_str.isdigit():
            total = False
            index = int(index_str)
        elif index_str != '':
            raise Exception("Element '" + index_str + "' in '" + params + "' is not supported")

        if not total and index < 0 and all_params:
            raise Exception("Cannot list all elements and parameters at the same '" + params + "' request")

        result = self.get_value(total)
        assert isinstance(result, tuple) or isinstance(result, list)
        #assert hasattr(result, '_asdict')
        #assert hasattr(result, '_fields')
        if index < 0:
            if all_params:  # not total
                assert isinstance(result, tuple)
                assert hasattr(result, '_asdict')
                return string_from_dict_optionally(result._asdict(), params_join)
            elif not total:
                return list_from_array_of_namedtupes(result, param, params, index_join)
            assert isinstance(result, tuple)
            assert hasattr(result, '_fields')
            if param in result._fields:
                return getattr(result, param)
            raise Exception(f"Element '{param}' in '{params}' is not supported")

        # index selected
        try:
            result = result[index]
            if all_params:
                #assert isinstance(result, namedtuple)
                return string_from_dict_optionally(result._asdict(), params_join)
            elif param in result._fields:
                return getattr(result, param)
            raise Exception(f"Element '{param}' in '{params}' is not supported")
        except IndexError:
            raise Exception(f"Element #{index} is not present")

    # noinspection PyMethodMayBeStatic
    def get_value(self, total:bool) -> Union[List[NamedTuple], NamedTuple]:
        raise Exception("Not implemented")


class NameOrTotalTupleCommandHandler(MethodCommandHandler):
    '''
    e.g. for calling psutil.net_io_counters
    '''

    def handle(self, params: list[str]) -> Payload:
        if len(params) != 1 and len(params) != 2:
            raise Exception(f"Exactly 1 or 2 parameters are supported for '{self.name}'; found {len(params)} parameters instead: {params}")

        param = params[0]
        name = params[1] if len(params) == 2 else None

        all_params = param == '*' or param == '*;'
        params_join = param.endswith(';')

        total = True
        index_join = False
        if name == '*':
            total = False
            name = None
        elif name == '*;':
            total = False
            index_join = True
            name = None
        elif name != '':
            total = False

        if not total and name is None and all_params:
            raise Exception("Cannot list all elements and parameters at the same '" + params + "' request")

        result = self.get_value(total)
        assert isinstance(result, tuple) or isinstance(result, dict)
        if name is None or name == '':
            if all_params:  # not total
                #assert isinstance(result, NamedTuple)
                assert isinstance(result, tuple)
                return string_from_dict_optionally(result._asdict(), params_join)
            if not total:
                return dict_from_dict_of_namedtupes(result, param, params, index_join)
            assert isinstance(result, tuple)
            if param in result._fields:
                return getattr(result, param)
            raise Exception(f"Element '{param}' in '{params}' is not supported")

        res = result[name]
        if all_params:
            return string_from_dict_optionally(res._asdict(), params_join)
        elif param in res._fields:
            return getattr(res, param)
        raise Exception(f"Parameter '{param}' in '{params}' is not supported")

    # noinspection PyMethodMayBeStatic
    def get_value(self, total:bool) -> Union[Dict[str, NamedTuple], NamedTuple]:
        raise Exception("Not implemented")

class DiskUsageCommandHandler(MethodCommandHandler):

    def __init__(self) -> None:
        super().__init__('disk_usage')
        return

    def handle(self, params: list[str]) -> Payload:
        if len(params) != 2:
            raise Exception(f"Exactly 2 parameters are supported for '{self.name}'; found {len(params)} parameters instead: {params}")

        param = params[0]
        disk = params[1]

        if disk == '':
            raise Exception("Disk ' in '" + self.name + "' should be specified")
        disk = disk.replace('|', '/')  # replace slashes with vertical slashes to do not conflict with MQTT topic name

        tup = self.get_value(disk)
        assert isinstance(tup, tuple)
        if param == '*' or param == '*;':
            return string_from_dict_optionally(tup._asdict(), param.endswith(';'))
        elif param in tup._fields:
            return getattr(tup, param)
        raise Exception("Parameter '" + param + "' in '" + self.name + "' is not supported")

    # noinspection PyMethodMayBeStatic
    def get_value(self, disk:str) -> NamedTuple:
        return psutil.disk_usage(disk)


class SensorsTemperaturesCommandHandler(MethodCommandHandler):

    def __init__(self) -> None:
        super().__init__('sensors_temperatures')
        return

    def handle(self, params: list[str]) -> Payload:
        '''
        '''

        if len(params) != 2 and len(params) != 3:
            raise Exception(f"Exactly 2 or 3 parameters are supported for '{self.name}'; found {len(params)} parameters instead: {params}")

        source = params[0]
        label = params[1]
        param = params[2] if len(params) == 3 else ''

        psutil_dict = self.get_value()
        # psutil_dict is a Dict[str, List[NamedTuple]]
        assert isinstance(psutil_dict, dict)

        if source == '*' or source == '*;':
            d = {k: [i.current for i in v] for k, v in psutil_dict.items()}
            return string_from_dict_optionally(d, source.endswith(';'))

        elif source in psutil_dict:
            llist = psutil_dict[source]
            if label == '' and param == '':
                return [i.current for i in llist]
            elif label == '*' or label == '*;':
                llist = [i._asdict() for i in llist]
                return string_from_dict_optionally(llist, label.endswith(';'))
            else:
                if isinstance(label, int):
                    temps = llist[label]
                else:
                    temps = next((x for x in llist if x.label == label), None)

                if temps is None:
                    raise Exception("Device '" + label + "' in '" + self.name + "' is not supported")
                if param == '':
                    return temps.current
                elif param == '*' or param == '*;':
                    return string_from_dict_optionally(temps._asdict(), param.endswith(';'))
                else:
                    return temps._asdict()[param]

        raise Exception("Sensor '" + source + "' in '" + self.name + "' is not supported")

class SensorsFansCommandHandler(MethodCommandHandler):
    '''
    '''
    def __init__(self) -> None:
        super().__init__('sensors_fans')
        return

    def handle(self, params:list[str]) -> Payload:
        tup = self.get_value()
        assert isinstance(tup, dict)

        source, param = split(params)
        if source == '*' or source == '*;':
            tup = {k: [i.current for i in v] for k, v in tup.items()}
            return string_from_dict_optionally(tup, source.endswith(';'))

        if source in tup:
            llist = tup[source]
            label, param = split(param)
            if label == '' and param == '':
                return [i.current for i in llist]
            elif label == '*' or label == '*;':
                llist = [i._asdict() for i in llist]
                return string_from_dict_optionally(llist, label.endswith(';'))
            else:
                temps = llist[int(label)] if label.isdigit() else next((x for x in llist if x.label == label), None)
                if temps is None:
                    raise Exception("Device '" + label + "' in '" + self.name + "' is not supported")
                if param == '':
                    return temps.current
                elif param == '*' or param == '*;':
                    return string_from_dict_optionally(temps._asdict(), param.endswith(';'))
                else:
                    return temps._asdict()[param]
        raise Exception("Fan '" + source + "' in '" + self.name + "' is not supported")


class ProcessesCommandHandler(CommandHandler):
    '''
    '''

    top_cpu_regexp = re.compile(r"^top_cpu(\[\d+\])*$")
    top_memory_regexp = re.compile(r"^top_memory(\[\d+\])*$")
    top_number_regexp = re.compile(r"^top_[a-z_]+\[(\d+)\]$")
    pid_file_regexp = re.compile(r"^pid\[(.*)\]$")
    name_pattern_regexp = re.compile(r"^name\[(.*)\]$")

    def __init__(self) -> None:
        super().__init__('processes')
        return

    def handle(self, params:list[str]) -> Payload:
        process, param = split(params)

        if process in ('*', '*;'):
            if param == '*':
                raise Exception(f"Parameter name in '{self.name}' should be specified")
            result = {p.pid: self.get_process_value(p, param, params)
                for p in psutil.process_iter()}
            return string_from_dict_optionally(result, process.endswith(';'))
        elif process.isdigit():
            pid = int(process)
        elif self.top_cpu_regexp.match(process):
            pid = self.find_process(process, lambda p: p.cpu_percent(), True)
        elif self.top_memory_regexp.match(process):
            pid = self.find_process(process, lambda p: p.memory_percent(), True)
        elif self.pid_file_regexp.match(process):
            m = self.pid_file_regexp.match(process)
            assert m is not None
            pid = self.get_pid_from_file(m.group(1).replace('|', '/'))
        elif self.name_pattern_regexp.match(process):
            m = self.name_pattern_regexp.match(process)
            assert m is not None
            pid = self.get_find_process(m.group(1))
        else:
            raise Exception("Process in '" + params + "' should be selected")

        if pid < 0:
            raise Exception("Process " + process + " not found")
        return self.get_process_value(
            psutil.Process(pid), param, params)

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
    def get_process_value(process:psutil.Process, params:list[str],
            all_params:list[str]) -> Any:
        prop, param = split(params)
        process_handler = process_handlers.get(prop, None)
        if process_handler is None:
            raise Exception(f"Parameter '{prop}' in '{all_params}' is not supported")

        return process_handler.handle(param, process)


class SmartCommandHandler(CommandHandler):
    '''
    Handler of commands addressed to SMART
    '''

    def __init__(self) -> None:
        '''

        '''
        super().__init__('smart')
        return

    def handle(self, params: list[str]) -> Payload:
        '''
        Will call self.get_value()
        '''

        if len(params) != 1 and len(params) != 2:
            raise Exception(f"Exactly 1 or 2 parameters are supported for '{self.name}'; found {len(params)} parameters instead: {params}")

        dev = params[0]
        param = params[1] if len(params) == 2 else ''
        
        self.name = dev
        self.device = SmartDevice(self.name)

        if self.device.serial is None:
            errmsg = f"Failed to read SMART data from '{self.name}': probably root permissions are required"
            logging.error(errmsg)
            raise Exception(errmsg)

        info = self.device.__getstate__()
        if param == '':
            return string_from_dict_optionally(info, True)
        elif param == '*':
            return string_from_dict_optionally(info, False)
        elif param == '*;':
            return string_from_dict_optionally(info, True)
        val = info.get(param, None)
        if val is not None:
            return val
        raise Exception(f"Parameter '{param}' is not supported")

    def get_value(self) -> Payload:
        raise Exception("Not implemented")


handlers = {
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
    'virtual_memory': TupleCommandHandler('virtual_memory'),
    'swap_memory': TupleCommandHandler('swap_memory'),
    'disk_partitions': IndexTupleCommandHandler('disk_partitions'),
    'disk_usage': DiskUsageCommandHandler(),

    'disk_io_counters': type(
        "DiskIOCountersCommandHandler",
        (IndexOrTotalTupleCommandHandler, object),
        {
            "get_value": lambda self, total:
                psutil.disk_io_counters(perdisk=not total)
        })('disk_io_counters'),

    'net_io_counters': type(
        "NetIOCountersCommandHandler",
        (NameOrTotalTupleCommandHandler, object),
        {
            "get_value": lambda self, total:
                psutil.net_io_counters(pernic=not total)
        })('net_io_counters'),

    'processes': ProcessesCommandHandler(),
    'users': IndexTupleCommandHandler('users'),
    'boot_time': ValueCommandHandler('boot_time'),
    'pids': IndexCommandHandler('pids'),
    'sensors_temperatures': SensorsTemperaturesCommandHandler(),
    'sensors_fans': SensorsFansCommandHandler(),
    'sensors_battery': TupleCommandHandler('sensors_battery'),
    'smart': SmartCommandHandler(),
}


class ProcessCommandHandler:
    '''

    '''
    def __init__(self, name:str):
        self.name = name

    def handle(self, param:str, process:psutil.Process) -> Payload:
        raise Exception("Not implemented")


class ProcessMethodCommandHandler(ProcessCommandHandler):
    def __init__(self, name:str):
        super().__init__(name)
        try:
            self.method = getattr(psutil.Process, self.name)
        except AttributeError:
            self.method = None  # method not defined
        return

    def handle(self, param:str, process:psutil.Process) -> Payload:
        if param != '':
            raise Exception(f"Parameter '{param}' in '{self.name}' is not supported")

        return self.get_value(process)

    def get_value(self, process:psutil.Process) -> Payload:
        if self.method is None:
            raise Exception(f"Not implemented: psutil.{self.name}")
        return self.method(process)


class ProcessPropertiesCommandHandler(ProcessCommandHandler):
    '''
    '''

    def __init__(self, name:str, join:bool, subproperties:bool):
        super().__init__(name)
        self.join = join
        self.subproperties = subproperties
        return

    def handle(self, param:str, process:psutil.Process) -> Payload:
        if param != '':
            raise Exception("Parameter '" + param + "' in '" + self.name + "' is not supported")

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

    def handle(self, param:str, process:psutil.Process) -> Payload:
        assert self.method is not None
        arr = self.method(process)

        if param == '*' or param == '*;':
            return string_from_list_optionally(arr, param.endswith(';'))
        elif param == 'count':
            return len(arr)
        elif param.isdigit():
            return arr[int(param)]
        #else:
        raise Exception(f"Parameter '{param}' in '{self.name}' is not supported")


class ProcessMethodTupleCommandHandler(ProcessMethodCommandHandler):

    def handle(self, param:str, process:psutil.Process) -> Payload:
        assert self.method is not None
        tup = self.method(process)
        if param == '*' or param == '*;':
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


def list_from_array_of_namedtupes(
        array_of_namedtupes: Union[List[Any], NamedTuple], key, func,
        join:bool = False) -> Union[List[Any], str]:
    result = list()
    for tup in array_of_namedtupes:
        if key in tup._fields:
            result.append(getattr(tup, key))
        else:
            raise Exception("Element '" + key + "' in '" + func + "' is not supported")
    return string_from_list_optionally(result, join)


def dict_from_dict_of_namedtupes(dict_of_namedtupes:Dict[str, NamedTuple],
        key:str, func, join=False) -> Union[Dict[str, Any], str]:
    result = dict()
    for name, tup in dict_of_namedtupes.items():
        if key in tup._fields:
            result[name] = getattr(tup, key)
        else:
            raise Exception(f"Element '{key}' in '{func}' is not supported")
    return string_from_dict_optionally(result, join)

def string_from_dict_optionally(d:Dict[Any,Any], join:bool) -> Union[Dict[Any,Any], str]:
    return string_from_dict(d) if join else d

def string_from_dict(d:Dict[Any,Any]) -> str:
    return json.dumps(d, sort_keys=True)

def string_from_list_optionally(lst:List[Any], join:bool) -> Union[List[Any], str]:
    return json.dumps(lst) if join else lst


def split(s: str) -> Tuple[str, str]:
    parts = s.split("/", 1)
    if len(parts) == 2:
        return parts[0], parts[1]
    return parts[0], ''

def get_value(handlerName: str, params: list[str], formatter: str) -> Payload:
    '''
    Main module API.
    Given a task definition, retrieves the sensor value via the corresponding Task/Handler and
    formats that sensor value with the corresponding formatter.
    '''
    handler = handlers.get(handlerName, None)
    if handler is None:
        raise Exception(f"Task '{handlerName}' is not supported")

    value = handler.handle(params)
    if formatter is not None:
        value = Formatter.format(formatter, value)

    logging.debug("get_value(%s with params %s) => %s provided by %s", handlerName, params, value, handler)
    return value

def get_supported_handlers() -> List[str]:
    '''
    Returns list of supported handlers
    '''
    return list(handlers.keys())
