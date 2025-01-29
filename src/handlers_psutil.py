# Copyright (c) 2016 psmqtt project
# Licensed under the MIT License.  See LICENSE file in the project root for full license information.

import psutil
from typing import (
    NamedTuple,
)

from .handlers_base import MethodCommandHandler, Payload
from .utils import string_from_dict_optionally

class DiskCountersIO(MethodCommandHandler):
    '''
    used by, e.g. cpu_times_percent
    '''
    def __init__(self, name:str):
        super().__init__(name)

    def handle(self, params: list[str]) -> Payload:
        assert isinstance(params, list)

        if len(params) != 1 and len(params) != 2:
            raise Exception(f"Exactly 1 or 2 parameters are supported for '{self.name}'; found {len(params)} parameters instead: {params}")

        disk = params[0]
        counter = params[1] if len(params) == 2 else ''

        all_params = counter == '*' or counter == '*;'
        params_join = counter.endswith(';')

        total = False
        #index_join = False
        if disk == '*':
            total = True
        elif disk == '*;':
            total = True
            #index_join = True

        result = self.get_value(total, disk)
        #if not isinstance(result, tuple):
        #    raise Exception(f"Expected a tuple, got: {type(result)}")

        if all_params:  # not total
            assert isinstance(result, tuple)
            assert hasattr(result, '_asdict')
            return string_from_dict_optionally(result._asdict(), params_join)

        assert isinstance(result, tuple)
        assert hasattr(result, '_fields')
        if counter in result._fields:
            return getattr(result, counter)
        raise Exception(f"Element '{counter}' in '{self.name}' is not supported")

    def get_value(self, total:bool, disk:str) -> NamedTuple:
        result = psutil.disk_io_counters(perdisk=not total)
        # result is a namedtuple when perdisk=False or a dict when perdisk=True
        if total:
            return result
        else:
            # the dictionary is indexed by just the device name e.g. "sda" and contains a tuple
            return result[disk.replace("/dev/", "")]


class DiskUsageCommandHandler(MethodCommandHandler):

    def __init__(self) -> None:
        super().__init__('disk_usage')
        return

    def handle(self, params: list[str]) -> Payload:
        assert isinstance(params, list)

        if len(params) != 2:
            raise Exception(f"Exactly 2 parameters are supported for '{self.name}'; found {len(params)} parameters instead: {params}")

        param = params[0]
        disk = params[1]

        if disk == '':
            raise Exception(f"Disk in '{self.name}' should be specified")
        disk = disk.replace('|', '/')  # replace slashes with vertical slashes to do not conflict with MQTT topic name

        tup = self.get_value(disk)
        assert isinstance(tup, tuple)
        if param == '*' or param == '*;':
            return string_from_dict_optionally(tup._asdict(), param.endswith(';'))
        elif param in tup._fields:
            return getattr(tup, param)
        raise Exception(f"Parameter '{param}' in '{self.name}' is not supported")

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
        assert isinstance(params, list)

        if len(params) != 1 and len(params) != 2 and len(params) != 3:
            raise Exception(f"Exactly 1, 2 or 3 parameters are supported for '{self.name}'; found {len(params)} parameters instead: {params}")

        source = params[0]
        label = params[1] if len(params) >= 2 else ''
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
                    raise Exception(f"Device '{label}' in '{self.name}' is not supported")
                if param == '':
                    return temps.current
                elif param == '*' or param == '*;':
                    return string_from_dict_optionally(temps._asdict(), param.endswith(';'))
                else:
                    return temps._asdict()[param]

        raise Exception(f"Sensor '{source}' in '{self.name}' is not supported")

class SensorsFansCommandHandler(MethodCommandHandler):
    '''
    '''
    def __init__(self) -> None:
        super().__init__('sensors_fans')
        return

    def handle(self, params:list[str]) -> Payload:
        assert isinstance(params, list)

        if len(params) < 1 or len(params) > 3:
            raise Exception(f"Exactly 1, 2 or 3 parameters are supported for '{self.name}'; found {len(params)} parameters instead: {params}")

        source = params[0]
        label = params[1] if len(params) >= 2 else ''
        param = params[2] if len(params) == 3 else ''

        tup = self.get_value()
        assert isinstance(tup, dict)

        if source == '*' or source == '*;':
            tup = {k: [i.current for i in v] for k, v in tup.items()}
            return string_from_dict_optionally(tup, source.endswith(';'))

        if source in tup:
            llist = tup[source]
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
        raise Exception(f"Fan '{source}' in '{self.name}' is not supported")
