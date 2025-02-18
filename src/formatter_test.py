# Copyright (c) 2016 psmqtt project
# Licensed under the MIT License.  See LICENSE file in the project root for full license information.

import unittest
import pytest

from .formatter import Formatter

@pytest.mark.unit
class TestFormatter(unittest.TestCase):

    def test_get_format(self) -> None:
        f = Formatter.get_format("123/ddd/ddd{{sdd}}/444")
        self.assertEqual("123/ddd", f[0])
        self.assertEqual("ddd{{sdd}}/444", f[1])

        f = Formatter.get_format("123/ddd/ddd{sdd}}/444")
        self.assertEqual("123/ddd/ddd{sdd}}/444", f[0])
        self.assertEqual(None, f[1])

        f = Formatter.get_format("ddd{{sdd}}/444")
        self.assertEqual("ddd{{sdd}}/444", f[0])
        self.assertEqual(None, f[1])

    def test_format(self) -> None:
        self.assertEqual("10", Formatter.format("{{a}}", {"a": 10}))
        self.assertEqual("10", Formatter.format("{{x}}", 10))
        self.assertEqual("3", Formatter.format("{{x[2]}}", [1, 2, 3]))
        self.assertEqual("2.0", Formatter.format("{{a/5}}", {"a": 10}))
        self.assertEqual("15", Formatter.format("{{a+b}}", {"a": 10, "b": 5}))
        self.assertEqual("1.2 MB", Formatter.format("{{a/1000000}} MB", {"a": 1200000}))
        self.assertEqual("1 MB", Formatter.format("{{a|MB}}", {"a": 1200000}))

    def test_format_uptime_str(self) -> None:
        import time
        n = int(time.time())
        self.assertEqual("0 min", Formatter.format("{{x|uptime_str}}", n))
        self.assertEqual("1 min", Formatter.format("{{x|uptime_str}}", n - 60))
        self.assertEqual("1:00", Formatter.format("{{x|uptime_str}}", n - 1*60*60))
        self.assertEqual("1:40", Formatter.format("{{x|uptime_str}}", n - 1*60*60 - 40*60))
        self.assertEqual("1 day, 0 min", Formatter.format("{{x|uptime_str}}", n - 24*60*60))
        self.assertEqual("1 day, 40 min", Formatter.format("{{x|uptime_str}}", n - 24*60*60 - 40*60))
        self.assertEqual("1 day, 1:40", Formatter.format("{{x|uptime_str}}", n - 25*60*60 - 40*60))
        self.assertEqual("2 days, 1:40", Formatter.format("{{x|uptime_str}}", n - 49*60*60 - 40*60))
        self.assertEqual("2 days, 1:39", Formatter.format("{{x|uptime_str}}", n - 49*60*60 - 40*60+30))
        self.assertEqual("2 days, 1:40", Formatter.format("{{x|uptime_str}}", n - 49*60*60 - 40*60-30))

    def test_format_uptime_sec(self) -> None:
        import time
        n = int(time.time())

        # "uptime_sec" should in theory product 0 secs of uptime, but indeed it takes some
        # time to do the computation so, in some rare cases, it might round the
        # time difference up to "1" sec, so we pass the test with both "0" and "1" outputs:
        self.assertIn(Formatter.format("{{x|uptime_sec}}", n), ["0", "1"])

        # same as above: we accept +/-1sec of skew:
        self.assertIn(Formatter.format("{{x|uptime_sec}}", n - 60), ["59", "60", "61"])

    def test_format_iso8601_str(self) -> None:
        epoch_time = 1706985600  # Example timestamp
        self.assertEqual("2024-02-03T18:40:00+00:00", Formatter.format("{{x|iso8601_str}}", epoch_time))

        epoch_time = 1686757139
        self.assertEqual("2023-06-14T15:38:59+00:00", Formatter.format("{{x|iso8601_str}}", epoch_time))
