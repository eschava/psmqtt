# Copyright (c) 2016 psmqtt project
# Licensed under the MIT License.  See LICENSE file in the project root for full license information.

import logging
import os
import shutil
import subprocess
import time

from .handlers_base import BaseHandler, Payload


class DirectoryUsageCommandHandler(BaseHandler):
    '''
    DirectoryUsageCommandHandler computes the size of a particular directory, in bytes
    This handler is implemented entirely inside PSMQTT and does not rely on psutil or other 3rd party libs
    '''

    def __init__(self) -> None:
        super().__init__('directory_usage')

        # check if the system where PSMQTT is running has the "du" utility installed
        self.has_du_utility = shutil.which("du") is not None
        logging.info("DirectoryUsageCommandHandler: du utility is %savailable", "" if self.has_du_utility else "NOT ")

        return

    def handle(self, params: list[str], caller_task_id: str) -> Payload:
        assert isinstance(params, list)

        if len(params) < 1:
            raise Exception(f"{self.name}: At least 1 parameter is required; found {len(params)} parameters instead: {params}")
        return self.get_value(params)

    def get_recursive_directory_size(self, start_path:str) -> int:
        '''
        Get the total (recursive) size of a directory in bytes.
        This method is cross-platform but is also _very_ slow for large folders.
        Use with care.
        '''
        start_time = time.time()
        total_size_bytes = 0

        if self.has_du_utility:

            # take the fast lane and delegate all the work to the "du" utility
            # this is typically up to 2x-3x faster than the python implementation
            # see e.g. https://stackoverflow.com/questions/1392413/calculating-a-directorys-size-using-python
            # here is some number I measured, in seconds:
            #
            #          PYTHON IMPL    DU IMPL
            # folder1: 9.66           3.37
            # folder2: 49.44          29.32
            # folder3: 7.48           3.96
            #
            # where these 3 folders contain real-world data and big dataset (> 400GB)
            try:
                total_size_kbytes = subprocess.check_output(['du','-sk', start_path]).split()[0].decode('utf-8')
            except subprocess.CalledProcessError as e:
                raise Exception(f"Error occurred while executing du command: {e}")

            total_size_bytes = int(total_size_kbytes) * 1024

        else:

            # python implementation:
            for dirpath, dirnames, filenames in os.walk(start_path):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    # skip if it is symbolic link
                    if not os.path.islink(fp):
                        total_size_bytes += os.path.getsize(fp)

        elapsed_time = time.time() - start_time
        logging.debug(f"Recursively computed size of directory {start_path} in {elapsed_time:.2f}seconds with {'du' if self.has_du_utility else 'python'} implemention: {total_size_bytes}bytes")
        return total_size_bytes

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
