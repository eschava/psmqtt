# Copyright (c) 2016 psmqtt project
# Licensed under the MIT License.  See LICENSE file in the project root for full license information.

import logging
import os
import time

from .handlers_base import BaseHandler, Payload


class DirectoryUsageCommandHandler(BaseHandler):
    '''
    DirectoryUsageCommandHandler computes the size of a particular directory, in bytes
    This handler is implemented entirely inside PSMQTT and does not rely on psutil or other 3rd party libs
    '''

    def __init__(self) -> None:
        super().__init__('directory_usage')
        return

    def handle(self, params: list[str], caller_task_id: str) -> Payload:
        assert isinstance(params, list)

        if len(params) < 1:
            raise Exception(f"{self.name}: At least 1 parameter is required; found {len(params)} parameters instead: {params}")
        return self.get_value(params)

    def get_recursive_directory_size(self, start_path:str):
        '''
        Get the total (recursive) size of a directory in bytes.
        This method is cross-platform but is also _very_ slow for large folders.
        Use with care.
        '''
        start_time = time.time()
        total_size_bytes = 0
        for dirpath, dirnames, filenames in os.walk(start_path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                # skip if it is symbolic link
                if not os.path.islink(fp):
                    total_size_bytes += os.path.getsize(fp)

        elapsed_time = time.time() - start_time
        logging.debug(f"Recursively computed size of directory {start_path} in {elapsed_time:.2f}seconds")

    # noinspection PyMethodMayBeStatic
    def get_value(self, directories: list[str]) -> int:

        total_size_bytes = 0
        for directory in directories:
            if directory == '':
                raise Exception(f"{self.name}: Found an empty directory in the parameters")
            if not os.path.exists(directory):
                raise Exception(f"{self.name}: Directory does not exist: {directory}")
            total_size_bytes += self.get_recursive_directory_size(directory)

        return total_size_bytes
