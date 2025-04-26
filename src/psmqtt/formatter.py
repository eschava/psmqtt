# Copyright (c) 2016 psmqtt project
# Licensed under the MIT License.  See LICENSE file in the project root for full license information.

import time
from datetime import datetime, timezone
from typing import Any
from jinja2 import Environment

default_num_decimal_digits = 2


# ---------------------------------------------------------------------------- #
#                                JINJA2 FILTERS                                #
# ---------------------------------------------------------------------------- #


# Please note that dividing by 1000 produces Kilobytes, Megabytes, Gigabytes, etc.
# This is not the same as dividing by 1024, which would produce Kibibytes, Mebibytes, Gibibytes, etc.
# The former is the SI standard, the latter is the IEC standard.

def jinja2_filter_kb(value:float) -> str:
    return str(value // 1000)

def jinja2_filter_mb(value:float) -> str:
    return str(value // 1000 // 1000)

def jinja2_filter_gb(value:float) -> str:
    return str(value // 1000 // 1000 // 1000)

# the _fractional variants return the value with a default number of 2 fractional digits
# (customizable providing a filter argument)

def jinja2_filter_kb_fractional(value:float, num_decimal_digits=default_num_decimal_digits) -> str:
    return str(round(value / 1000, num_decimal_digits))

def jinja2_filter_mb_fractional(value:float, num_decimal_digits=default_num_decimal_digits) -> str:
    return str(round(value / (1000 * 1000), num_decimal_digits))

def jinja2_filter_gb_fractional(value:float, num_decimal_digits=default_num_decimal_digits) -> str:
    return str(round(value / (1000 * 1000 * 1000), num_decimal_digits))


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
    env.filters['KB_fractional'] = jinja2_filter_kb_fractional
    env.filters['MB_fractional'] = jinja2_filter_mb_fractional
    env.filters['GB_fractional'] = jinja2_filter_gb_fractional
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

    def format(self, value: Any) -> str:
        '''
        Format the provided value (either dictionary or sequence or scalar) according to the
        template string provided at the constructor
        '''
        return self.jinja2_template.render(value if isinstance(value, dict) else {"x": value})

    def get_template(self) -> str:
        '''
        Return the Jinja2 template string provided at the constructor
        '''
        return self.jinja2_template_str
