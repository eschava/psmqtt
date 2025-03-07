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

class TaskParam:
    @staticmethod
    def is_wildcard(param: str) -> bool:
        return param == "*" or param == "+"

    @staticmethod
    def is_regular_wildcard(param: str) -> bool:
        return param == "*"

    @staticmethod
    def is_join_wildcard(param: str) -> bool:
        return param == "+"

class BaseHandler:
    '''
    Abstract base class that has a handle() method.
    All task handlers will inherit from this base class.

    Note that the only truly public API of all handlers inheriting from this class is the handle() method.
    The get_value() method is "protected" and should not be called from outside the class.
    '''

    def __init__(self, name:str):
        self.name = name
        return

    def handle(self, params: list[str], caller_task_id: str) -> Payload:
        '''
        The handle() function is the core function of an handler:
        it typically performs 3 steps in sequence:
        1. validation of the input parameters
        2. invoke the psutil/pySMART function via get_value() accessor function
        3. filter of the output and conversion to "Payload" type

        The 'caller_task_id' is a string that identifies the task that is invoking this handler.
        This is useful only to stateful handlers, which need to store a state that is different
        from task to task.

        The return value of this function is a "Payload" type, which is a generic type that can be
        1. single-valued types: str, float, int
        2. multi-valued types:
           * list: in this case every list item will be published in a different MQTT subtopic,
                   obtained using the list item index as last MQTT topic separator
           * dict: in this case every (key,value) pair will be published in a different MQTT subtopic
                   using the "key" as last MQTT topic separator
           * namedtuple: in this case every (field,value) pair will be published in a different MQTT subtopic
                   using the "field" as last MQTT topic separator
        '''
        assert isinstance(params, list)
        raise Exception("Not implemented")

    def get_value(self) -> Payload:
        raise Exception("Not implemented")


class MethodCommandHandler(BaseHandler):
    '''
    MethodCommandHandler is a BaseHandler with a self.method pointing to a psutil function,
    e.g. psutil.cpu_percent(), boot_time.
    Provides a get_value() function that invokes self.method and just returns its value.

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

    def get_value(self) -> Payload:
        '''
        Invokes the psutil function pointed by self.method.
        '''
        if self.method is None:
            raise Exception(f"psutil '{self.name}' not implemented")
        return self.method()

class ValueCommandHandler(MethodCommandHandler):
    '''
    ValueCommandHandler provides an handle() function that just returns the
    output of the get_value() function.
    This is a good class to be used when no parameters are expected.
    '''

    def handle(self, params: list[str], caller_task_id: str) -> Payload:
        '''
        Will call self.get_value()
        '''
        assert isinstance(params, list)
        if len(params) > 0:
            raise Exception(f"{self.name}: Parameter '{params}' is not supported")

        return self.get_value()

class IndexCommandHandler(MethodCommandHandler):
    '''
    IndexCommandHandler handles psutil functions that return a list, e.g. the psutil.pids() function.
    '''

    def handle(self, params: list[str], caller_task_id: str) -> Payload:
        assert isinstance(params, list)

        arr = self.get_value()
        assert isinstance(arr, list)

        if len(params) != 1:
            raise Exception(f"{self.name}: exactly 1 parameter is required; found {len(params)} parameters instead: {params}")

        index_str = params[0]
        if TaskParam.is_wildcard(index_str):
            return string_from_list_optionally(arr, TaskParam.is_join_wildcard(index_str))
        elif index_str == 'count':
            return len(arr)
        elif isinstance(index_str, int):
            return arr[index_str]
        elif index_str.isdigit():
            return arr[int(index_str)]
        raise Exception(f"{self.name}: Parameter '{index_str}' is not supported as index")


class TupleCommandHandler(MethodCommandHandler):
    '''
    TupleCommandHandler handles psutil functions that return a named
    tuple, e.g. psutil.cpu_times, psutil.cpu_stats, psutil.virtual_memory, psutil.swap_memory
    '''

    def handle(self, params: list[str], caller_task_id: str) -> Payload:
        assert isinstance(params, list)

        tup = self.get_value()
        if tup is None:
            # this might happen when psutil didn't find ANY hardware support;
            # e.g. on a computer that has no battery, the psutil.sensors_battery() returns None
            return "None"

        assert isinstance(tup, tuple)

        if len(params) != 1:
            raise Exception(f"{self.name}: exactly 1 parameter is required; found {len(params)} parameters instead: {params}")

        # the parameter for this handler decides which tuple field we should select:
        tuple_field = params[0]
        if TaskParam.is_regular_wildcard(tuple_field):
            return tup._asdict()
        if TaskParam.is_join_wildcard(tuple_field):
            return string_from_dict(tup._asdict())
        elif tuple_field in tup._fields:
            return getattr(tup, tuple_field)
        elif tuple_field == '':
            raise Exception(f"{self.name}: Parameter should be selected")
        raise Exception(f"{self.name}: Parameter '{tuple_field}' is not supported")


class IndexTupleCommandHandler(MethodCommandHandler):
    '''
    IndexTupleCommandHandler handles psutil functions that return a
    list of named tuples, e.g. psutil.disk_partitions, psutil.users
    '''

    def handle(self, params: list[str], caller_task_id: str) -> Payload:
        '''
        This handler accepts 1 or 2 parameters.
        The first parameter shall be:
        * a field name appearing inside the tuples
        * wildcard
        The second parameter shall be:
        * the index of a particular tuple
        '''
        assert isinstance(params, list)

        if len(params) != 1 and len(params) != 2:
            raise Exception(f"{self.name}: exactly 1 or 2 parameters are required; found {len(params)} parameters instead: {params}")

        field_selector = params[0]
        index_str = params[1] if len(params) >= 2 else ''

        all_fields = TaskParam.is_wildcard(field_selector)
        index = -1

        if isinstance(field_selector, int):
            all_fields = True
            index = field_selector
        elif field_selector.isdigit():
            all_fields = True
            index = int(field_selector)
        elif isinstance(index_str, int):
            index = index_str
        elif index_str.isdigit():
            index = int(index_str)
        elif not TaskParam.is_wildcard(index_str):
            raise Exception(f"{self.name}: Element '{index_str}' in '{params}' is not supported")

        if index < 0 and all_fields:
            raise Exception(f"{self.name}: Cannot list all fields from all results into the same task")

        result = self.get_value()
        assert isinstance(result, list)
        if index < 0:
            # no index selected: select the same field from ALL tuples
            return list_from_array_of_namedtuples(result, field_selector, self.name, TaskParam.is_join_wildcard(index_str))
        else:  # index selected
            try:
                elt = result[index]
                if all_fields:
                    return string_from_dict_optionally(elt._asdict(), TaskParam.is_join_wildcard(field_selector))
                elif field_selector in elt._fields:
                    return getattr(elt, field_selector)
                else:
                    raise Exception(f"{self.name}: Parameter '{field_selector}' is not supported")
            except IndexError:
                raise Exception(f"{self.name}: Element #{index} is not present")


class IndexOrTotalCommandHandler(BaseHandler):
    '''
    IndexOrTotalCommandHandler handles psutil functions that return a list of values.
    Differently from IndexCommandHandler, this class requires a get_value() implementation
    taking 1 boolean parameter "total".

    This class is used to handle some psutil functions that support the possibility to return the
    TOTAL quantity of something, e.g. cpu usage.
    '''
    def __init__(self, name:str):
        super().__init__(name)
        return

    def handle(self, params: list[str], caller_task_id: str) -> Payload:
        assert isinstance(params, list)

        total = True
        join = False
        count = False
        index = -1
        if len(params) != 0 and len(params) != 1:
            raise Exception(f"{self.name}: Exactly 0 or 1 parameters are required; found {len(params)} parameters instead: {params}")

        param = params[0] if len(params) == 1 else ''

        if TaskParam.is_regular_wildcard(param):
            total = False
        elif TaskParam.is_join_wildcard(param):
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
            raise Exception(f"{self.name}: Parameter '{param}' is not supported")
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
            raise Exception(f"{self.name}: Element #{index} is not present")

    # noinspection PyMethodMayBeStatic
    def get_value(self, total:bool) -> List[Any]:
        '''
        cpu_percent is not using this
        '''
        raise Exception("Not implemented")


class IndexOrTotalTupleCommandHandler(MethodCommandHandler):
    '''
    IndexOrTotalTupleCommandHandler handles psutil functions that return a list of named tuples.
    Differently from IndexTupleCommandHandler, this class requires a get_value() implementation
    taking 1 boolean parameter "total".

    This class is used to handle some psutil functions that support the possibility to return the
    TOTAL quantity of something, e.g. detailed cpu usage from psutil.cpu_times_percent().
    '''
    def __init__(self, name:str):
        super().__init__(name)

    def handle(self, params: list[str], caller_task_id: str) -> Payload:
        assert isinstance(params, list)

        if len(params) != 1 and len(params) != 2:
            raise Exception(f"{self.name}: Exactly 1 or 2 parameters are required; found {len(params)} parameters instead: {params}")

        param = params[0]
        index_str = params[1] if len(params) == 2 else ''

        all_params = TaskParam.is_wildcard(param)
        params_join = TaskParam.is_join_wildcard(param)

        total = True
        index_join = False
        index = -1
        if TaskParam.is_regular_wildcard(index_str):
            total = False
        elif TaskParam.is_join_wildcard(index_str):
            total = False
            index_join = True
        elif isinstance(index_str, int):
            total = False
            index = index_str
        elif index_str.isdigit():
            total = False
            index = int(index_str)
        elif index_str != '':
            raise Exception(f"{self.name}: Element '{index_str}' is not supported")

        if not total and index < 0 and all_params:
            raise Exception(f"{self.name}: Cannot list all elements and parameters at the same '{params}' request")

        result = self.get_value(total)
        if not isinstance(result, tuple) and not isinstance(result, list):
            raise Exception(f"{self.name}: Unexpected type from psutil.{self.name} with total={total}: {type(result)}; {isinstance(result, tuple)}; {isinstance(result, list)};")
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
            raise Exception(f"{self.name}: Element '{param}' in '{params}' is not supported")

        # index selected
        try:
            result = result[index]
            if all_params:
                #assert isinstance(result, namedtuple)
                return string_from_dict_optionally(result._asdict(), params_join)
            elif param in result._fields:
                return getattr(result, param)
            raise Exception(f"{self.name}: Element '{param}' in '{params}' is not supported")
        except IndexError:
            raise Exception(f"{self.name}: Element #{index} is not present")

    # noinspection PyMethodMayBeStatic
    def get_value(self, total:bool) -> Union[List[NamedTuple], NamedTuple]:
        raise Exception("Not implemented")


class NameOrTotalTupleCommandHandler(MethodCommandHandler):
    '''
    IndexOrTotalTupleCommandHandler handles psutil functions that return a named tuple
    or a dictionary of named tuples, like psutil.net_io_counters().
    '''

    def handle(self, params: list[str], caller_task_id: str) -> Payload:
        assert isinstance(params, list)

        if len(params) != 1 and len(params) != 2:
            raise Exception(f"{self.name}: Exactly 1 or 2 parameters are required; found {len(params)} parameters instead: {params}")

        param = params[0]
        name = params[1] if len(params) == 2 else None

        all_params = TaskParam.is_wildcard(param)
        params_join = TaskParam.is_join_wildcard(param)

        total = True
        index_join = False
        if TaskParam.is_regular_wildcard(name):
            total = False
            name = None
        elif TaskParam.is_join_wildcard(name):
            total = False
            index_join = True
            name = None
        elif name != '' and name is not None:
            total = False

        if not total and name is None and all_params:
            raise Exception(f"{self.name}: Cannot list all elements and parameters at the same '{params}' request")

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
            raise Exception(f"{self.name}: Element '{param}' in '{params}' is not supported")

        res = result[name]
        if all_params:
            return string_from_dict_optionally(res._asdict(), params_join)
        elif param in res._fields:
            return getattr(res, param)
        raise Exception(f"{self.name}: Parameter '{param}' in '{params}' is not supported")

    # noinspection PyMethodMayBeStatic
    def get_value(self, total:bool) -> Union[Dict[str, NamedTuple], NamedTuple]:
        raise Exception("Not implemented")
