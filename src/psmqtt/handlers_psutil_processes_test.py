# Copyright (c) 2016 psmqtt project
# Licensed under the MIT License.  See LICENSE file in the project root for full license information.

import os
import unittest
from unittest.mock import Mock, patch

import pytest
import psutil

from .handlers_psutil_processes import (
    ProcessMethodCommandHandler,
    ProcessPropertiesCommandHandler,
    ProcessesCommandHandler,
    process_handlers,
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
        current_pid = os.getpid()
        current_name = ''
        for k,v in processes.items():
            assert isinstance(k, int)
            assert isinstance(v, str)
            if k == current_pid:
                current_name = v

        self.assertTrue(current_name)

        res = handler.handle([f'{current_pid}','name'], fake_task_id)
        self.assertEqual(res, current_name)

        processes = handler.handle(['top_cpu','name'], fake_task_id)
        self.assertIsInstance(processes, str)

        processes = handler.handle(['top_memory','exe'], fake_task_id)
        self.assertIsInstance(processes, str)

        pid = handler.handle([f'name[{current_name}]','pid'], fake_task_id)
        self.assertIsInstance(pid, int)
        return

    def test_find_process_skips_disappeared_processes(self) -> None:
        disappeared_process = Mock(pid=1)
        disappeared_process.memory_percent.side_effect = psutil.NoSuchProcess(1)
        active_process = Mock(pid=2)
        active_process.memory_percent.return_value = 10.0

        handler = ProcessesCommandHandler()
        with patch(
            'psmqtt.handlers_psutil_processes.psutil.process_iter',
            return_value=[disappeared_process, active_process],
        ):
            pid = handler.find_process(
                'top_memory', lambda process: process.memory_percent(), True
            )

        self.assertEqual(pid, 2)

    def test_wildcard_skips_inaccessible_processes(self) -> None:
        inaccessible_process = Mock(pid=1)
        active_process = Mock(pid=2)

        handler = ProcessesCommandHandler()
        with (
            patch(
                'psmqtt.handlers_psutil_processes.psutil.process_iter',
                return_value=[inaccessible_process, active_process],
            ),
            patch.object(
                ProcessesCommandHandler,
                'get_process_value',
                side_effect=[psutil.AccessDenied(pid=1), 'active'],
            ),
        ):
            processes = handler.handle(['*', 'name'], fake_task_id)

        self.assertEqual(processes, {2: 'active'})

    def test_top_process_skips_inaccessible_property(self) -> None:
        inaccessible_process = Mock(pid=1)
        inaccessible_process.memory_percent.return_value = 20.0
        accessible_process = Mock(pid=2)
        accessible_process.memory_percent.return_value = 10.0

        handler = ProcessesCommandHandler()
        with (
            patch(
                'psmqtt.handlers_psutil_processes.psutil.process_iter',
                return_value=[inaccessible_process, accessible_process],
            ),
            patch.object(
                ProcessesCommandHandler,
                'get_process_value',
                side_effect=[psutil.AccessDenied(pid=1), '/bin/active'],
            ),
        ):
            executable = handler.handle(['top_memory', 'exe'], fake_task_id)

        self.assertEqual(executable, '/bin/active')

    def test_process_properties_skips_permission_errors(self) -> None:
        property_handler = Mock(spec=ProcessMethodCommandHandler)
        property_handler.method = Mock()
        property_handler.handle.side_effect = PermissionError
        properties_handler = ProcessPropertiesCommandHandler('*;', True, False)

        with patch.dict(process_handlers, {'exe': property_handler}, clear=True):
            properties = properties_handler.handle([], Mock())

        self.assertEqual(properties, '{}')
