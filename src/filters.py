import time
from jinja2 import Environment  # pip install jinja2

def kb(value:int) -> str:
    return str(value // 1024) + " KB"


def mb(value:int) -> str:
    return str(value // 1024 // 1024) + " MB"


def gb(value:int) -> str:
    return str(value // 1024 / 1024 // 1024) + " GB"


def uptime(boot_time:float) -> str:
    upt = time.time() - boot_time

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

def uptimesec(boot_time: float) -> int:
    upt = time.time() - boot_time
    return round(upt)


def register_filters(env: Environment) -> None:
    env.filters['KB'] = kb
    env.filters['MB'] = mb
    env.filters['GB'] = gb
    env.filters['uptime'] = uptime
    env.filters['uptimesec'] = uptimesec
    return
