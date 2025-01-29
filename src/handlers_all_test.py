# Copyright (c) 2016 psmqtt project
# Licensed under the MIT License.  See LICENSE file in the project root for full license information.

import unittest
import pytest

from .handlers_all import (
    TaskHandlers
)

@pytest.mark.unit
class TestHandlers(unittest.TestCase):

    def test_get_value(self) -> None:
        val = TaskHandlers.get_value('cpu_percent', [], None)
        self.assertIsInstance(val, float)

        val = TaskHandlers.get_value('virtual_memory', ['percent'], None)
        self.assertIsInstance(val, float)

        return
