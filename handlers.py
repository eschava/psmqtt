import re
import psutil  # pip install psutil


class CommandHandler:
    def __init__(self, name):
        self.name = name

    def handle(self, params):
        raise Exception("Not implemented")


class TupleCommandHandler(CommandHandler):
    def __init__(self, method_name):
        CommandHandler.__init__(self, method_name)
        self.method = getattr(psutil, method_name)

    def handle(self, params):
        tup = self.get_value()
        if params == '*':
            return tup._asdict()
        if params == '*;':
            return string_from_dict(tup._asdict())
        elif params in tup._fields:
            return getattr(tup, params)
        elif params == '':
            raise Exception("Parameter in '" + self.name + "' should be selected")
        else:
            raise Exception("Parameter '" + params + "' in '" + self.name + "' is not supported")

    def get_value(self):
        return self.method()


class IndexTupleCommandHandler(CommandHandler):
    def __init__(self, name):
        CommandHandler.__init__(self, name)

    def handle(self, params):
        param, index_str = split(params)
        all_params = param == '' or param == '*'
        index = -1

        if param.isdigit():
            all_params = True
            index = int(param)
        elif index_str.isdigit():
            index = int(index_str)
        elif index_str != '' and index_str != '*':
            raise Exception("Element '" + index_str + "' in '" + params + "' is not supported")

        if index < 0 and all_params:
            raise Exception("Cannot list all elements and parameters at the same '" + params + "' request")

        result = self.get_value()
        if index < 0:
            return list_from_array_of_namedtupes(result, param, params)
        else:  # index selected
            try:
                result = result[index]
                if all_params:
                    return result._asdict()
                elif param in result._fields:
                    return getattr(result, param)
                else:
                    raise Exception("Parameter '" + param + "' in '" + params + "' is not supported")
            except IndexError:
                raise Exception("Element #" + str(index) + " is not present")

    # noinspection PyMethodMayBeStatic
    def get_value(self):
        raise Exception("Not implemented")


class IndexOrTotalCommandHandler(CommandHandler):
    def __init__(self, name):
        CommandHandler.__init__(self, name)

    def handle(self, params):
        total = True
        join = False
        index = -1
        if params == '*':
            total = False
        elif params == '*;':
            total = False
            join = True
        elif params.isdigit():
            total = False
            index = int(params)
        elif params != '':
            raise Exception("Parameter '" + params + "' in '" + self.name + "' is not supported")

        try:
            result = self.get_value(total)
            return string_from_list_optionally(result, join) if index < 0 else result[index]
        except IndexError:
            raise Exception("Element #" + str(index) + " is not present")

    # noinspection PyMethodMayBeStatic
    def get_value(self, total):
        raise Exception("Not implemented")


class IndexOrTotalTupleCommandHandler(CommandHandler):
    def __init__(self, name):
        CommandHandler.__init__(self, name)

    def handle(self, params):
        param, index_str = split(params)
        all_params = param == '' or param == '*'
        total = True
        index = -1
        if index_str == '*':
            total = False
        elif index_str.isdigit():
            total = False
            index = int(index_str)
        elif index_str != '':
            raise Exception("Element '" + index_str + "' in '" + params + "' is not supported")

        if not total and index < 0 and all_params:
            raise Exception("Cannot list all elements and parameters at the same '" + params + "' request")

        result = self.get_value(total)
        if index < 0:
            if all_params:  # not total
                return result._asdict()
            else:
                if not total:
                    return list_from_array_of_namedtupes(result, param, params)
                elif param in result._fields:
                    return getattr(result, param)
                else:
                    raise Exception("Element '" + param + "' in '" + params + "' is not supported")
        else:  # index selected
            try:
                result = result[index]
                if all_params:
                    return result._asdict()
                elif param in result._fields:
                    return getattr(result, param)
                else:
                    raise Exception("Parameter '" + param + "' in '" + params + "' is not supported")
            except IndexError:
                raise Exception("Element #" + str(index) + " is not present")

    # noinspection PyMethodMayBeStatic
    def get_value(self, total):
        raise Exception("Not implemented")


class DiskUsageCommandHandler(CommandHandler):
    def __init__(self, name):
        CommandHandler.__init__(self, name)

    def handle(self, params):
        param, disk = split(params)
        if disk == '':
            disk = param
            param = ''
        if disk == '':
            disk = '/'

        tup = psutil.disk_usage(disk)
        if param == '*' or param == '':
            return tup._asdict()
        elif param in tup._fields:
            return getattr(tup, param)
        else:
            raise Exception("Parameter '" + param + "' in '" + self.name + "' is not supported")


class ProcessesCommandHandler(CommandHandler):
    top_cpu_regexp = re.compile("^top_cpu(\[\d+\])*$")
    top_memory_regexp = re.compile("^top_memory(\[\d+\])*$")
    top_number_regexp = re.compile("^top_[a-z_]+\[(\d+)\]$")

    def __init__(self, name):
        CommandHandler.__init__(self, name)

    def handle(self, params):
        process, param = split(params)

        pid = -1
        all_params = param == '' or param == '*'
        if process == '*':
            if all_params:
                raise Exception("Parameter name in '" + self.name + "' should be specified")
        elif process.isdigit():
            pid = int(process)
        elif self.top_cpu_regexp.match(process):
            pid = self.find_process(process, lambda p: p._cpu_percent, True)
        elif self.top_memory_regexp.match(process):
            pid = self.find_process(process, lambda p: p._mempercent, True)
        else:
            raise Exception("Process in '" + params + "' should be selected")

        if pid < 0:
            raise Exception("All processes is not supported yet")
        else:
            process = psutil.Process(pid)
            props = param.split(" ")
            # TODO: support * parameter
            values = map(lambda p: self.get_process_value(process, p, params), props)
            return " ".join(values)

    def find_process(self, request, cmp_func, reverse):
        procs = []
        for p in psutil.process_iter():
            p._mempercent = p.memory_percent()
            p._cpu_percent = p.cpu_percent()
            procs.append(p)
        procs = sorted(procs, key=cmp_func, reverse=reverse)
        m = self.top_number_regexp.match(request)
        index = 0 if m is None else int(m.group(1))
        return procs[index].pid

    @staticmethod
    def get_process_value(process, params, all_params):
        prop, param = split(params)
        if prop in process_handlers:
            return str(process_handlers[prop].get_value(param, process))
        else:
            raise Exception("Parameter '" + prop + "' in '" + all_params + "' is not supported")


class ProcessMethodCommandHandler(CommandHandler):
    def __init__(self, name):
        CommandHandler.__init__(self, name)

    def get_value(self, param, process):
        method = getattr(psutil.Process, self.name)
        return method(process)


class ProcessMethodTupleCommandHandler(CommandHandler):
    def __init__(self, name):
        CommandHandler.__init__(self, name)

    def get_value(self, param, process):
        method = getattr(psutil.Process, self.name)
        tup = method(process)
        if param in tup._fields:
            return getattr(tup, param)
        else:
            raise Exception("Parameter '" + param + "' in '" + self.name + "' is not supported")


handlers = {
    'cpu_times': TupleCommandHandler('cpu_times'),

    'cpu_percent': type("CpuPercentCommandHandler", (IndexOrTotalCommandHandler, object),
                        {"get_value": lambda self, total: psutil.cpu_percent(percpu=not total)})('cpu_percent'),

    'cpu_times_percent': type("CpuTimesPercentCommandHandler", (IndexOrTotalTupleCommandHandler, object),
                              {"get_value": lambda self, total: psutil.cpu_times_percent(percpu=not total)})('cpu_times_percent'),

    'cpu_stats': TupleCommandHandler('cpu_stats'),

    'virtual_memory': TupleCommandHandler('virtual_memory'),

    'swap_memory': TupleCommandHandler('swap_memory'),

    'disk_partitions': type("DiskPartitionsCommandHandler", (IndexTupleCommandHandler, object),
                            {"get_value": lambda self: psutil.disk_partitions()})('disk_partitions'),

    'disk_usage': DiskUsageCommandHandler('disk_usage'),

    'disk_io_counters': type("DiskIOCountersCommandHandler", (IndexOrTotalTupleCommandHandler, object),
                             {"get_value": lambda self, total: psutil.disk_io_counters(perdisk=not total)})('disk_io_counters'),

    'processes': ProcessesCommandHandler('processes'),

    'users': type("UsersCommandHandler", (IndexTupleCommandHandler, object),
                  {"get_value": lambda self: psutil.users()})('users'),
}

process_handlers = {
    'name': ProcessMethodCommandHandler('name'),
    'exe': ProcessMethodCommandHandler('exe'),
    'cwd': ProcessMethodCommandHandler('cwd'),
    'uids': ProcessMethodTupleCommandHandler('uids'),
    'gids': ProcessMethodTupleCommandHandler('gids'),
    'cpu_times': ProcessMethodTupleCommandHandler('cpu_times'),
    'cpu_percent': ProcessMethodCommandHandler('cpu_percent'),
    'memory_percent': ProcessMethodCommandHandler('memory_percent'),
    'memory_info': ProcessMethodTupleCommandHandler('memory_info'),
    'memory_full_info': ProcessMethodTupleCommandHandler('memory_full_info'),
    'io_counters': ProcessMethodTupleCommandHandler('io_counters'),
    'num_threads': ProcessMethodCommandHandler('num_threads'),
    'nice': ProcessMethodCommandHandler('nice'),
    'num_ctx_switches': ProcessMethodTupleCommandHandler('num_ctx_switches'),
}


def list_from_array_of_namedtupes(array_of_namedtupes, key, func):
    result = list()
    for tup in array_of_namedtupes:
        if key in tup._fields:
            result.append(getattr(tup, key))
        else:
            raise Exception("Element '" + key + "' in '" + func + "' is not supported")
    return result


def string_from_dict(d):
    pairs = list()
    for key in d:
        pairs.append(key + "=" + str(d[key]))
    return ";".join(pairs)


def string_from_list_optionally(l, join):
    return ";".join(map(str, l)) if join else l


def split(s):
    parts = s.split("/", 1)
    return parts if len(parts) == 2 else [parts[0], '']
