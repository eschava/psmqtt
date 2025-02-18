# Copyright (c) 2016 psmqtt project
# Licensed under the MIT License.  See LICENSE file in the project root for full license information.

import time
from datetime import datetime, timezone
from typing import Any, Optional, Text, Tuple
from jinja2 import Environment

def kb(value:int) -> str:
    return str(value // 1024) + " KB"


def mb(value:int) -> str:
    return str(value // 1024 // 1024) + " MB"


def gb(value:int) -> str:
    return str(value // 1024 / 1024 // 1024) + " GB"


def uptime_str(linux_epoch_sec:float) -> str:
    upt = time.time() - linux_epoch_sec

    retval = ""
    days = int(upt / (60 * 60 * 24))

    if days != 0:
        retval += str(days) + " " + ("days" if days > 1 else "day") + ", "

    minutes = int(upt / 60)
    hours = int(minutes / 60)
    hours %= 24
    minutes %= 60

    if hours != 0:
        retval += str(hours) + ":" + (str(minutes) if minutes >= 10 else "0" + str(minutes))
    else:
        retval += str(minutes) + " min"

    return retval

def uptime_sec(linux_epoch_sec: float) -> int:
    upt = time.time() - linux_epoch_sec
    return round(upt)

def iso8601_str(linux_epoch_sec: float) -> str:
    return datetime.fromtimestamp(linux_epoch_sec, tz=timezone.utc).isoformat()


def register_filters() -> Environment:
    env = Environment()
    env.filters['KB'] = kb
    env.filters['MB'] = mb
    env.filters['GB'] = gb
    env.filters['uptime_str'] = uptime_str
    env.filters['uptime_sec'] = uptime_sec
    env.filters['iso8601_str'] = iso8601_str
    return env

class Formatter:
    '''
    Provides formatters to be applied to the task outputs before they get published
    to the MQTT broker
    '''
    env = register_filters()

    @classmethod
    def get_format(cls, path:str) -> Tuple[str, Optional[str]]:
        '''
        Tuple would be a better choice for typing
        '''
        i = path.find("{{")
        if i > 0:
            i = path.rfind("/", 0, i)
            if i > 0:
                return (path[0:i], path[i+1:])
        return (path, None)

    @classmethod
    def format(cls, f:str, value: Any) -> Text:
        return cls.env.from_string(f).render(
            value if isinstance(value, dict) else {"x": value})
