# Copyright (c) 2016 psmqtt project
# Licensed under the MIT License.  See LICENSE file in the project root for full license information.

import psutil
from typing import (
    NamedTuple,
)

from .handlers_base import MethodCommandHandler, NameOrTotalTupleCommandHandler, Payload, TaskParam
from .handlers_derived import RateHandler
from .utils import string_from_dict_optionally

class DiskIOCountersCommandHandler(MethodCommandHandler):
    '''
    DiskIOCountersCommandHandler handles the output of psutil.disk_io_counters()
    https://psutil.readthedocs.io/en/latest/#psutil.disk_io_counters
    '''
    def __init__(self):
        super().__init__('disk_io_counters')

    def handle(self, params: list[str], caller_task_id: str) -> Payload:
        assert isinstance(params, list)

        if len(params) != 1 and len(params) != 2:
            raise Exception(f"{self.name}: Exactly 1 or 2 parameters are required; found {len(params)} parameters instead: {params}")

        # first parameter is the field to select "read_bytes", "write_bytes", etc.
        field_selector = params[0]
        join_fields = TaskParam.is_join_wildcard(field_selector)

        # second parameter (if given) is the disk name, or a wildcard to select all disks
        disk = params[1] if len(params) == 2 else ''

        perdisk = disk != ''
        if TaskParam.is_join_wildcard(disk):
            perdisk = True
            join_fields = True

        if TaskParam.is_wildcard(field_selector) and TaskParam.is_wildcard(disk):
            raise Exception(f"{self.name}: Two wildcard parameters were provided but only one of the two can be a wildcard")

        result = self.get_value(perdisk, disk)

        if isinstance(result, tuple):
            if TaskParam.is_wildcard(field_selector):
                assert hasattr(result, '_asdict')
                return string_from_dict_optionally(result._asdict(), join_fields)
            elif field_selector in result._fields:
                return getattr(result, field_selector)
            else:
                raise Exception(f"{self.name}: Field '{field_selector}' is not supported")

        elif isinstance(result, dict):
            if TaskParam.is_wildcard(field_selector):
                return string_from_dict_optionally(result, join_fields)
            else:
                # select an individual field inside the namedtuple associated with each key in the dictionary:
                filtereddict = {k: getattr(v, field_selector) for k,v in result.items()}
                #for
                return filtereddict

        else:
            raise Exception(f"{self.name}: Unexpected result type: {type(result)}")

    def get_value(self, perdisk:bool, disk:str) -> NamedTuple:

        result = psutil.disk_io_counters(perdisk=perdisk)
        # result is a namedtuple when perdisk=False or a dict when perdisk=True

        disk_without_dev = disk.replace('/dev/', '')
        if not perdisk:
            # this is already a (named)tuple:
            return result

        # handle the case where result is a dict:
        # the dictionary is indexed by the device name e.g. "/dev/sda" and contains a tuple
        if disk_without_dev in result:
            return result[disk_without_dev]
        elif TaskParam.is_wildcard(disk):
            # just return the whole dictionary -- the caller might apply a field selector though
            return result
        else:
            avail_disks = ','.join(["/dev/" + x for x in result.keys()])
            raise Exception(f"{self.name}: Disk '{disk}' is not valid. Available disks: {avail_disks}")


class DiskIOCountersRateHandler(RateHandler):
    '''
    DiskIOCountersRateHandler computes the rate of change of the disk I/O counters.
    This is often more useful than the monotonically-increasing raw disk I/O counters.
    '''

    def __init__(self) -> None:
        super().__init__('disk_io_counters_rate', DiskIOCountersCommandHandler())
        return

class DiskUsageCommandHandler(MethodCommandHandler):
    '''
    DiskUsageCommandHandler handles the output of psutil.disk_usage()
    '''

    def __init__(self) -> None:
        super().__init__('disk_usage')
        return

    def handle(self, params: list[str], caller_task_id: str) -> Payload:
        assert isinstance(params, list)

        if len(params) != 2:
            raise Exception(f"{self.name}: Exactly 2 parameters are required; found {len(params)} parameters instead: {params}")

        field_selector = params[0]
        disk = params[1]

        if disk == '':
            raise Exception(f"{self.name}: Disk should be specified")
        disk = disk.replace('|', '/')  # replace slashes with vertical slashes to do not conflict with MQTT topic name

        tup = self.get_value(disk)
        assert isinstance(tup, tuple)
        if TaskParam.is_wildcard(field_selector):
            return string_from_dict_optionally(tup._asdict(), TaskParam.is_join_wildcard(field_selector))
        elif field_selector in tup._fields:
            return getattr(tup, field_selector)
        raise Exception(f"{self.name}: Parameter '{field_selector}' is not supported")

    # noinspection PyMethodMayBeStatic
    def get_value(self, disk:str) -> NamedTuple:
        return psutil.disk_usage(disk)


class NetIOCountersCommandHandler(NameOrTotalTupleCommandHandler):
    '''
    NetIOCountersCommandHandler handles the output of psutil.net_io_counters()
    '''

    def __init__(self) -> None:
        super().__init__('net_io_counters')
        return

    def get_value(self, total:bool) -> Payload:
        return psutil.net_io_counters(pernic=not total)


class NetIOCountersRateHandler(RateHandler):
    '''
    NetIOCountersRateHandler computes the rate of change of the network I/O counters.
    This is often more useful than the monotonically-increasing raw network I/O counters.
    '''

    def __init__(self) -> None:
        super().__init__('net_io_counters_rate', NetIOCountersCommandHandler())
        return


class SensorsTemperaturesCommandHandler(MethodCommandHandler):
    '''
    SensorsTemperaturesCommandHandler handles the output of psutil.sensors_temperatures()
    '''

    def __init__(self) -> None:
        super().__init__('sensors_temperatures')
        return

    def handle(self, params: list[str], caller_task_id: str) -> Payload:
        '''
        '''
        assert isinstance(params, list)

        if len(params) != 1 and len(params) != 2 and len(params) != 3:
            raise Exception(f"{self.name}: Exactly 1, 2 or 3 parameters are required; found {len(params)} parameters instead: {params}")

        source = params[0]
        label = params[1] if len(params) >= 2 else ''
        param = params[2] if len(params) == 3 else ''

        psutil_dict = self.get_value()
        # psutil_dict is a Dict[str, List[NamedTuple]]
        assert isinstance(psutil_dict, dict)

        if TaskParam.is_wildcard(source):
            d = {k: [i.current for i in v] for k, v in psutil_dict.items()}
            return string_from_dict_optionally(d, TaskParam.is_join_wildcard(source))

        elif source in psutil_dict:
            llist = psutil_dict[source]
            if label == '' and param == '':
                return [i.current for i in llist]
            elif TaskParam.is_wildcard(label):
                llist = [i._asdict() for i in llist]
                return string_from_dict_optionally(llist, TaskParam.is_join_wildcard(label))
            else:
                if isinstance(label, int):
                    temps = llist[label]
                else:
                    temps = next((x for x in llist if x.label == label), None)

                if temps is None:
                    raise Exception(f"{self.name}: Device '{label}' is not supported")
                if param == '':
                    return temps.current
                elif TaskParam.is_wildcard(param):
                    return string_from_dict_optionally(temps._asdict(), TaskParam.is_join_wildcard(param))
                else:
                    return temps._asdict()[param]

        raise Exception(f"{self.name}: Sensor '{source}' is not supported")

class SensorsFansCommandHandler(MethodCommandHandler):
    '''
    SensorsFansCommandHandler handles the output of psutil.sensors_fans()
    '''
    def __init__(self) -> None:
        super().__init__('sensors_fans')
        return

    def handle(self, params:list[str], caller_task_id: str) -> Payload:
        assert isinstance(params, list)

        if len(params) < 1 or len(params) > 3:
            raise Exception(f"{self.name}: Exactly 1, 2 or 3 parameters are required; found {len(params)} parameters instead: {params}")

        source = params[0]
        label = params[1] if len(params) >= 2 else ''
        param = params[2] if len(params) == 3 else ''

        tup = self.get_value()
        assert isinstance(tup, dict)

        if TaskParam.is_wildcard(source):
            tup = {k: [i.current for i in v] for k, v in tup.items()}
            return string_from_dict_optionally(tup, TaskParam.is_join_wildcard(source))

        if source in tup:
            llist = tup[source]
            if label == '' and param == '':
                return [i.current for i in llist]
            elif TaskParam.is_wildcard(label):
                llist = [i._asdict() for i in llist]
                return string_from_dict_optionally(llist, TaskParam.is_join_wildcard(label))
            else:
                temps = llist[int(label)] if label.isdigit() else next((x for x in llist if x.label == label), None)
                if temps is None:
                    raise Exception(f"{self.name}: Device '{label}' is not supported")
                if param == '':
                    return temps.current
                elif TaskParam.is_wildcard(param):
                    return string_from_dict_optionally(temps._asdict(), TaskParam.is_join_wildcard(param))
                else:
                    return temps._asdict()[param]
        raise Exception(f"{self.name}: Fan '{source}' is not supported")

class GetLoadAvgCommandHandler(MethodCommandHandler):
    '''
    GetLoadAvgCommandHandler handles the output of psutil.getloadavg()
    '''
    def __init__(self) -> None:
        super().__init__('getloadavg')
        return

    def handle(self, params:list[str], caller_task_id: str) -> Payload:
        assert isinstance(params, list)

        if len(params) != 1 and len(params) != 2:
            raise Exception(f"{self.name}: Exactly 1 or 2 parameters are required; found {len(params)} parameters instead: {params}")

        field = params[0]
        percent_or_abs = params[1] if len(params) == 2 else 'percent'

        avgload = self.get_value()
        assert isinstance(avgload, tuple)

        if percent_or_abs == 'percent':
            avgload = [x / psutil.cpu_count() * 100 for x in avgload]
        elif percent_or_abs == 'abs' or percent_or_abs == 'absolute':
            pass
        else:
            raise Exception(f"{self.name}: Invalid parameter '{percent_or_abs}': either 'percent' or 'abs' is expected")

        if TaskParam.is_wildcard(field):
            loadavg_dict = {
                'last1min': avgload[0],
                'last5min': avgload[1],
                'last15min': avgload[2],
            }
            return string_from_dict_optionally(loadavg_dict, TaskParam.is_join_wildcard(field))

        if field == 'last1min':
            return avgload[0]
        elif field == 'last5min':
            return avgload[1]
        elif field == 'last15min':
            return avgload[2]

        raise Exception(f"{self.name}: Field '{field}' is not supported: expected 'last1min', 'last5min' or 'last15min'")
