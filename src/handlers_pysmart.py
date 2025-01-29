# Copyright (c) 2016 psmqtt project
# Licensed under the MIT License.  See LICENSE file in the project root for full license information.

import logging
from pySMART import Device as SmartDevice
from typing import (
    List,
)

from .handlers_base import BaseHandler, Payload
from .utils import string_from_dict_optionally

class SmartCommandHandler(BaseHandler):
    '''
    Provides readings of S.M.A.R.T. counters via pySMART library
    '''

    def __init__(self) -> None:
        '''

        '''
        super().__init__('smart')
        return

    def handle(self, params: List[str]) -> Payload:
        '''
        Will call self.get_value()
        '''
        assert isinstance(params, list)
        if len(params) != 1 and len(params) != 2:
            raise Exception(f"{self.name}: Exactly 1 or 2 parameters are required; found {len(params)} parameters instead: {params}")

        dev = params[0]
        param = params[1] if len(params) == 2 else ''
        self.name = dev
        self.device = SmartDevice(self.name)

        if self.device.serial is None:
            errmsg = f"{self.name}: Failed to read SMART data: probably root permissions are required"
            logging.error(errmsg)
            raise Exception(errmsg)

        info = self.device.__getstate__()

        # delete 2 fields that are actually very cluttered fields repeating all the other dictionary keys:
        del info["attributes"]
        del info["if_attributes"]

        if param == '':
            return string_from_dict_optionally(info, True)
        elif BaseHandler.is_regular_wildcard(param):
            return string_from_dict_optionally(info, False)
        elif BaseHandler.is_join_wildcard(param):
            return string_from_dict_optionally(info, True)
        val = info.get(param, None)
        if val is not None:
            return val
        raise Exception(f"{self.name}: Parameter '{param}' is not supported")

    def get_value(self) -> Payload:
        raise Exception("Not implemented")
