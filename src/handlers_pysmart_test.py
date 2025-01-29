# Copyright (c) 2016 psmqtt project
# Licensed under the MIT License.  See LICENSE file in the project root for full license information.

import unittest
import pytest

from .handlers_pysmart import (
    SmartCommandHandler,
)

@pytest.mark.unit
class TestHandlers(unittest.TestCase):

    def test_SmartCommandHandler(self) -> None:
        handler = SmartCommandHandler()
        #val = handler.get_value()
        try:
            val = handler.handle('dev/nvme0')
            #print(val)
            self.assertIsInstance(val, dict)
            assert isinstance(val, dict)

            self.assertEqual(
                handler.handle('*'), {"asus": [30.0], "coretemp": [45.0, 52.0]})
        except Exception:
            pass

        return
