# Copyright (c) 2016 psmqtt project
# Licensed under the MIT License.  See LICENSE file in the project root for full license information.

from pySMART import Device as SmartDevice
from typing import (
    List,
)

from .handlers_base import BaseHandler, Payload
from .utils import string_from_dict_optionally
from .handlers_base import TaskParam

class SmartCommandHandler(BaseHandler):
    '''
    Provides readings of S.M.A.R.T. counters via pySMART library
    '''

    def __init__(self) -> None:
        super().__init__('smart')
        return

    def handle(self, params: List[str], caller_task_id: str) -> Payload:
        '''
        Takes 2 parameters:
        * device name
        * parameter name or wildcard
        '''
        assert isinstance(params, list)
        if len(params) != 1 and len(params) != 2:
            raise Exception(f"{self.name}: Exactly 1 or 2 parameters are required; found {len(params)} parameters instead: {params}")

        device = params[0]
        field = params[1] if len(params) == 2 else ''

        #if TaskParam.is_wildcard(dev) and TaskParam.is_wildcard(param):
        #    raise Exception(f"{self.name}: Cannot list all SMART fields from all disks into the same task")

        info = self.get_value(device)
        #logging.debug(f"{info}")

        if field == '':
            return string_from_dict_optionally(info, True)
        elif TaskParam.is_join_wildcard(field):
            return string_from_dict_optionally(info, True)
        elif TaskParam.is_regular_wildcard(field):
            return string_from_dict_optionally(info, False)

        # specific field requested
        val = info.get(field, None)
        if val is not None:
            return val
        raise Exception(f"{self.name}: Parameter '{field}' is not supported for device '{device}'")

    def get_value(self, dev: str) -> Payload:
        '''
        Uses methods of pySMART to acquire SMART counters
        '''
        smart_data = SmartDevice(dev)
        if smart_data.serial is None:
            raise Exception(f"{self.name}: Failed to read SMART data for device '{dev}': probably root permissions are required")

        # __getstate__() is a non-documented magic function returning some _selected_
        # fields of the SmartDevice class into a dictionary, which is easier to index in psmqtt
        info = smart_data.__getstate__()

        # explode the "attributes" entry to dictionary keys in the form
        #  attribute_raw[ATTRIBUTE_NAME]=RAW_VALUE
        for a in info["attributes"]:
            if a is not None:
                assert isinstance(a, dict)
                assert "name" in a
                assert "raw" in a
                info[f"attribute_raw[{a['name']}]"] = a["raw"]

        # explode the "tests" entry to dictionary keys in the form
        #  tests[TEST_NUM]=JSON
        # sort the tests in such a way that test[0] is always the most recent one (having the highest "hours" value)
        try:
            sorted_test_list = sorted(smart_data.tests, key=lambda x: int(x.hours), reverse=True)
        except ValueError:
            # failed casting to int... use the pySMART sorting
            sorted_test_list = smart_data.tests
        idx = 0
        for t in sorted_test_list:
            info[f"test[{idx}]"] = dict(t.__getstate__())
            idx += 1

        # delete fields that are useless after the flattening of SMART attributes and SMART tests just done:
        del info["attributes"]
        del info["if_attributes"]
        del info["tests"]

        return info
