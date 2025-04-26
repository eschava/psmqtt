# Copyright (c) 2016 psmqtt project
# Licensed under the MIT License.  See LICENSE file in the project root for full license information.

import unittest
import pytest

from .handlers_psutil_processes import (
    ProcessesCommandHandler
)

fake_task_id = "0.0"

@pytest.mark.unit
class TestHandlers(unittest.TestCase):

    def test_ProcessesCommandHandler(self) -> None:
        handler = ProcessesCommandHandler()
        processes = handler.handle(['*','name'], fake_task_id)
        self.assertIsInstance(processes, dict)
        assert isinstance(processes, dict)
        self.assertGreater(len(processes), 3)
        last_pid = 0
        last_name = ''
        for k,v in processes.items():
            if not last_name:
                assert isinstance(k, int)
                last_pid = k
                last_name = v
            assert isinstance(k, int)
            assert isinstance(v, str)
            assert isinstance(k, int)

        res = handler.handle([f'{last_pid}','name'], fake_task_id)
        self.assertEqual(res, last_name)

        processes = handler.handle(['top_cpu','name'], fake_task_id)
        self.assertIsInstance(processes, str)

        processes = handler.handle(['top_memory','exe'], fake_task_id)
        self.assertIsInstance(processes, str)

        pid = handler.handle([f'name[{last_name}]','pid'], fake_task_id)
        self.assertEqual(pid, last_pid)
        return
