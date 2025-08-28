# Copyright (c) 2016 psmqtt project
# Licensed under the MIT License.  See LICENSE file in the project root for full license information.

import unittest
from typing import List
import pytest

from .handlers_embedded import (
    DirectoryUsageCommandHandler
)

fake_task_id = "0.0"
directories = ["/test1", "/test2/"]

@pytest.mark.unit
class TestHandlers(unittest.TestCase):

    def test_MockedDirectoryUsageCommandHandler(self) -> None:
        handler = type("TestHandler", (DirectoryUsageCommandHandler, object),
                       {"get_value": lambda s,d: self._directory_usage_get_value(directories)})()
        # basic/dummy check
        self.assertEqual(1000000, handler.handle(directories, fake_task_id))
        # exceptions
        self.assertRaises(Exception, handler.handle, [], fake_task_id)

    def _directory_usage_get_value(self, dirs: List[str]) -> int:
        return 1000000

    def test_DiskUsageCommandHandler(self) -> None:
        handler = DirectoryUsageCommandHandler()

        # check we emit errors for non-existing directories:
        self.assertRaises(Exception, handler.handle,
                          ['/non-existing-directory-on-whatever-host-is-running-this-unit-test'], fake_task_id)

        return
