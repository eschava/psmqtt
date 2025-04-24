# Copyright (c) 2016 psmqtt project
# Licensed under the MIT License.  See LICENSE file in the project root for full license information.

import unittest
import pytest

from .formatter import Formatter

@pytest.mark.unit
class TestFormatter(unittest.TestCase):

    def test_generic_format(self) -> None:
        # the format() function can take a dictionary, a single value or a sequence
        self.assertEqual("10", Formatter("{{a}}").format({"a": 10}))
        self.assertEqual("10", Formatter("{{x}}").format(10))
        self.assertEqual("3", Formatter("{{x[2]}}").format([1, 2, 3]))
        self.assertEqual("2.0", Formatter("{{a/5}}").format({"a": 10}))
        self.assertEqual("15", Formatter("{{a+b}}").format({"a": 10, "b": 5}))
        self.assertEqual("1.2 MB", Formatter("{{a/1000000}} MB").format({"a": 1200000}))

    def test_byte_conversion_filters(self) -> None:
        tests = [

            {
                "input_value": 1200000,
                "input": "{{a|KB}}",
                "expected_output": "1200",
            },
            {
                "input_value": 1200000,
                "input": "{{a|MB}}",
                "expected_output": "1",
            },
            {
                "input_value": 1200000,
                "input": "{{a|GB}}",
                "expected_output": "0",
            },

            {
                "input_value": 1234000,
                "input": "{{a|MB_fractional}}",
                "expected_output": "1.23",
            },
            {
                "input_value": 1234567,
                "input": "{{a|MB_fractional(4)}}",
                "expected_output": "1.2346",  # note there is rounding here 1.234567 -> 1.2346
            },
            {
                "input_value": 1234567,
                "input": "{{a|KB_fractional(3)}}",
                "expected_output": "1234.567",
            },
        ]

        for t in tests:
            self.assertEqual(t["expected_output"],
                                Formatter(t["input"]).format({"a": t["input_value"]}))

    def test_format_uptime_str(self) -> None:
        import time
        n = int(time.time())
        self.assertEqual("0 min", Formatter("{{x|uptime_str}}").format(n))
        self.assertEqual("1 min", Formatter("{{x|uptime_str}}").format(n - 60))
        self.assertEqual("1:00", Formatter("{{x|uptime_str}}").format(n - 1*60*60))
        self.assertEqual("1:40", Formatter("{{x|uptime_str}}").format(n - 1*60*60 - 40*60))
        self.assertEqual("1 day, 0 min", Formatter("{{x|uptime_str}}").format(n - 24*60*60))
        self.assertEqual("1 day, 40 min", Formatter("{{x|uptime_str}}").format(n - 24*60*60 - 40*60))
        self.assertEqual("1 day, 1:40", Formatter("{{x|uptime_str}}").format(n - 25*60*60 - 40*60))
        self.assertEqual("2 days, 1:40", Formatter("{{x|uptime_str}}").format(n - 49*60*60 - 40*60))
        self.assertEqual("2 days, 1:39", Formatter("{{x|uptime_str}}").format(n - 49*60*60 - 40*60+30))
        self.assertEqual("2 days, 1:40", Formatter("{{x|uptime_str}}").format(n - 49*60*60 - 40*60-30))

    def test_format_uptime_sec(self) -> None:
        import time
        n = int(time.time())

        # "uptime_sec" should in theory product 0 secs of uptime, but indeed it takes some
        # time to do the computation so, in some rare cases, it might round the
        # time difference up to "1" sec, so we pass the test with both "0" and "1" outputs:
        self.assertIn(Formatter("{{x|uptime_sec}}").format(n), ["0", "1"])

        # same as above: we accept +/-1sec of skew:
        self.assertIn(Formatter("{{x|uptime_sec}}").format(n - 60), ["59", "60", "61"])

    def test_format_iso8601_str(self) -> None:
        epoch_time = 1706985600  # Example timestamp
        self.assertEqual("2024-02-03T18:40:00+00:00", Formatter("{{x|iso8601_str}}").format(epoch_time))

        epoch_time = 1686757139
        self.assertEqual("2023-06-14T15:38:59+00:00", Formatter("{{x|iso8601_str}}").format(epoch_time))
