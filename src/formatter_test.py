import unittest

from .formatter import Formatter

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

    def test_format_uptime(self) -> None:
        import time
        n = int(time.time())
        self.assertEqual("0 min", Formatter.format("{{x|uptime}}", n))
        self.assertEqual("1 min", Formatter.format("{{x|uptime}}", n - 60))
        self.assertEqual("1:00", Formatter.format("{{x|uptime}}", n - 1*60*60))
        self.assertEqual("1:40", Formatter.format("{{x|uptime}}", n - 1*60*60 - 40*60))
        self.assertEqual("1 day, 0 min", Formatter.format("{{x|uptime}}", n - 24*60*60))
        self.assertEqual("1 day, 40 min", Formatter.format("{{x|uptime}}", n - 24*60*60 - 40*60))
        self.assertEqual("1 day, 1:40", Formatter.format("{{x|uptime}}", n - 25*60*60 - 40*60))
        self.assertEqual("2 days, 1:40", Formatter.format("{{x|uptime}}", n - 49*60*60 - 40*60))
        self.assertEqual("2 days, 1:39", Formatter.format("{{x|uptime}}", n - 49*60*60 - 40*60+30))
        self.assertEqual("2 days, 1:40", Formatter.format("{{x|uptime}}", n - 49*60*60 - 40*60-30))


if __name__ == '__main__':
    unittest.main()
