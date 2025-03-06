# Copyright (c) 2016 psmqtt project
# Licensed under the MIT License.  See LICENSE file in the project root for full license information.

import time
from datetime import datetime, timezone
from typing import Any
from jinja2 import Environment


# ---------------------------------------------------------------------------- #
#                                JINJA2 FILTERS                                #
# ---------------------------------------------------------------------------- #

def jinja2_filter_kb(value:int) -> str:
    return str(value // 1024) + " KB"

def jinja2_filter_mb(value:int) -> str:
    return str(value // 1024 // 1024) + " MB"

def jinja2_filter_gb(value:int) -> str:
    return str(value // 1024 / 1024 // 1024) + " GB"

def jinja2_filter_uptime_str(linux_epoch_sec:float) -> str:
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

def jinja2_filter_uptime_sec(linux_epoch_sec: float) -> int:
    upt = time.time() - linux_epoch_sec
    return round(upt)

def jinja2_filter_iso8601_str(linux_epoch_sec: float) -> str:
    return datetime.fromtimestamp(linux_epoch_sec, tz=timezone.utc).isoformat()

def register_jinja2_filters() -> Environment:
    env = Environment()
    env.filters['KB'] = jinja2_filter_kb
    env.filters['MB'] = jinja2_filter_mb
    env.filters['GB'] = jinja2_filter_gb
    env.filters['uptime_str'] = jinja2_filter_uptime_str
    env.filters['uptime_sec'] = jinja2_filter_uptime_sec
    env.filters['iso8601_str'] = jinja2_filter_iso8601_str
    return env

# ---------------------------------------------------------------------------- #
#                                   FORMATTER                                  #
# ---------------------------------------------------------------------------- #

class Formatter:
    '''
    Provides formatters to be applied to the task outputs before they get published
    to the MQTT broker
    '''
    env = register_jinja2_filters()

    def __init__(self, jinja2_template_str: str) -> None:
        self.jinja2_template_str = jinja2_template_str
        self.jinja2_template = Formatter.env.from_string(jinja2_template_str)

    # @classmethod
    # def get_format(cls, path:str) -> Tuple[str, Optional[str]]:
    #     '''
    #     Tuple would be a better choice for typing
    #     '''
    #     i = path.find("{{")
    #     if i > 0:
    #         i = path.rfind("/", 0, i)
    #         if i > 0:
    #             return (path[0:i], path[i+1:])
    #     return (path, None)

    def format(self, value: Any) -> str:
        return self.jinja2_template.render(value if isinstance(value, dict) else {"x": value})

    def get_template(self) -> str:
        return self.jinja2_template_str
