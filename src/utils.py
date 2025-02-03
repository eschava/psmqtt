# Copyright (c) 2016 psmqtt project
# Licensed under the MIT License.  See LICENSE file in the project root for full license information.

import json
import uuid
from typing import Any, Dict, List, Union, NamedTuple

def list_from_array_of_namedtuples(
        array_of_namedtupes: Union[List[Any], NamedTuple], key:str, func:str,
        join:bool = False) -> Union[List[Any], str]:
    result = list()
    for tup in array_of_namedtupes:
        if key in tup._fields:
            result.append(getattr(tup, key))
        else:
            raise Exception(f"Element '{key}' in '{func}' is not supported")
    return string_from_list_optionally(result, join)


def dict_from_dict_of_namedtupes(dict_of_namedtupes:Dict[str, NamedTuple],
        key:str, func:str, join=False) -> Union[Dict[str, Any], str]:
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

def get_mac_address():
    # TODO we should try to get the MAC address of the specific network interface used
    # by the TCP connection to the MQTT broker...
    mac_num = uuid.getnode()
    mac = '-'.join((('%012X' % mac_num)[i:i+2] for i in range(0, 12, 2)))
    return mac
