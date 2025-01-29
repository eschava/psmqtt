# Copyright (c) 2016 psmqtt project
# Licensed under the MIT License.  See LICENSE file in the project root for full license information.

import logging
import psutil
from typing import (
    Any,
    Callable,
    Dict,
    List,
    NamedTuple,
    Optional,
    Sized,
    Union
)

from .utils import list_from_array_of_namedtuples, dict_from_dict_of_namedtupes, string_from_dict_optionally, string_from_dict, string_from_list_optionally

# all command handlers will return from their handle() function a Payload:
Payload = Union[List[Any], Dict[str, Any], NamedTuple, str, float, int]

class CommandHandler:
    '''
    Abstract base class that has a handle() method.
    All task handlers will inherit from this base class.
    '''

    def __init__(self, name:str):
        self.name = name
        return

    def handle(self, params: list[str]) -> Payload:
        '''
        Will call self.get_value()
        '''
        assert isinstance(params, list)
        raise Exception("Not implemented")

    def get_value(self) -> Payload:
        raise Exception("Not implemented")

class MethodCommandHandler(CommandHandler):
    '''
    CommandHandler with self.method pointing to psutil function,
    e.g. psutil.cpu_percent(), boot_time.
    handle invokes self.method and just returns its value.

    E.g. if the "cpu_percent" name is provided in the ctor, then this class will
    return the output of "psutil.cpu_percent()" from its get_value() function.
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

        assert isinstance(params, list)
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
        assert isinstance(params, list)
        if params != []:
            raise Exception(f"Parameter '{params}' in '{self.name}' is not supported")

        return self.get_value()

class IndexCommandHandler(MethodCommandHandler):
    '''
    CommandHandler with self.method pointing to psutil function returning a
    list, e.g. pids
    '''

    def handle(self, params: list[str]) -> Payload:
        assert isinstance(params, list)

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
        elif isinstance(param, int):
            return arr[param]
        elif param.isdigit():
            return arr[int(param)]
        raise Exception(f"Parameter '{param}' in '{self.name}' is not supported")


class TupleCommandHandler(MethodCommandHandler):
    '''
    CommandHandler with self.method pointing to a psutil function returning a
    tuple, e.g. cpu_times, cpu_stats, virtual_memory, swap_memory
    '''

    def handle(self, params: list[str]) -> Payload:
        assert isinstance(params, list)

        tup = self.get_value()
        if tup is None:
            # this might happen when psutil didn't find ANY hardware support;
            # e.g. on a computer that has no battery, the psutil.sensors_battery() returns None
            return "None"
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
        '''
        This handler accepts 1 or 2 parameters.
        The first parameter must be either:
        * is the index of the element in the list of named tuples.
        '''
        assert isinstance(params, list)

        if len(params) == 0:
            raise Exception(f"Found 0 parameters, need 1 or 2 in '{self.name}'")

        param = params[0]
        index_str = params[1] if len(params) >= 2 else ''

        all_params = param == '*' or param == '*;'
        index = -1

        if isinstance(param, int):
            all_params = True
            index = param
        elif param.isdigit():
            all_params = True
            index = int(param)
        elif isinstance(index_str, int):
            index = index_str
        elif index_str.isdigit():
            index = int(index_str)
        elif index_str != '*' and index_str != '*;':
            raise Exception(f"Element '{index_str}' in '{params}' is not supported")

        if index < 0 and all_params:
            raise Exception(f"Cannot list all elements and parameters into the same '{self.name}' request")

        result = self.get_value()
        assert isinstance(result, list)
        if index < 0:
            return list_from_array_of_namedtuples(result, param, self.name, index_str.endswith(';'))
        else:  # index selected
            try:
                elt = result[index]
                if all_params:
                    return string_from_dict_optionally(elt._asdict(), param.endswith(';'))
                elif param in elt._fields:
                    return getattr(elt, param)
                else:
                    raise Exception(f"Parameter '{param}' in '{self.name}' is not supported")
            except IndexError:
                raise Exception(f"Element #{index} is not present")

class IndexOrTotalCommandHandler(CommandHandler):
    '''
    CommandHandler with self.method pointing to a psutil function which
    returns a ??, e.g. psutils.cpu_percent.
    '''
    def __init__(self, name:str):
        super().__init__(name)
        return

    def handle(self, params: list[str]) -> Payload:
        assert isinstance(params, list)

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
        elif isinstance(param, int):
            total = False
            index = param
        elif param.isdigit():
            total = False
            index = int(param)
        elif param != '':
            raise Exception(f"Parameter '{param}' in '{self.name}' is not supported")
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
            raise Exception(f"Element #{index} is not present")

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
        assert isinstance(params, list)

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
        elif isinstance(index_str, int):
            total = False
            index = index_str
        elif index_str.isdigit():
            total = False
            index = int(index_str)
        elif index_str != '':
            raise Exception(f"Element '{index_str}' in '{self.name}' is not supported")

        if not total and index < 0 and all_params:
            raise Exception(f"Cannot list all elements and parameters at the same '{params}' request")

        result = self.get_value(total)
        if not isinstance(result, tuple) and not isinstance(result, list):
            raise Exception(f"Unexpected type from psutil.{self.name} with total={total}: {type(result)}; {isinstance(result, tuple)}; {isinstance(result, list)};")
        #assert hasattr(result, '_asdict')
        #assert hasattr(result, '_fields')
        if index < 0:
            if all_params:  # not total
                assert isinstance(result, tuple)
                assert hasattr(result, '_asdict')
                return string_from_dict_optionally(result._asdict(), params_join)
            elif not total:
                return list_from_array_of_namedtuples(result, param, self.name, index_join)
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
        assert isinstance(params, list)

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
        elif name != '' and name is not None:
            total = False

        if not total and name is None and all_params:
            raise Exception(f"Cannot list all elements and parameters at the same '{params}' request")

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
