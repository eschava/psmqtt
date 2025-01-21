import unittest
import pytest

from .topic import Topic

def get_subtopic(topic:str, param:str) -> str:
    t = Topic(topic)
    return t.get_subtopic(param) if t.is_multitopic() else topic

@pytest.mark.unit
class TopicTest(unittest.TestCase):

    def test_get_subtopic(self) -> None:
        self.assertEqual("/haha", get_subtopic('/haha', 'a'))
        self.assertEqual("/a", get_subtopic('/*', 'a'))
        self.assertEqual("/a", get_subtopic('/**', 'a'))
        self.assertEqual("/a/*", get_subtopic('/*/*', 'a'))
        self.assertEqual("/a/**", get_subtopic('/*/**', 'a'))
        self.assertEqual("/a/**", get_subtopic('/**/**', 'a'))

        # wildcard inside brackets
        self.assertEqual("/name[ppp*]/a", get_subtopic('/name[ppp*]/**', 'a'))
        self.assertEqual("/name[ppp*]/*;", get_subtopic('/name[ppp*]/*;', 'a'))
        self.assertEqual("/name[ppp*]/haha", get_subtopic('/name[ppp*]/haha', 'a'))
        self.assertEqual("/a/name[ppp*]/**", get_subtopic('/*/name[ppp*]/**', 'a'))
        self.assertEqual("/a/name[ppp*]/**", get_subtopic('/**/name[ppp*]/**', 'a'))
        self.assertEqual("/*;/name[ppp*]/a", get_subtopic('/*;/name[ppp*]/**', 'a'))
        self.assertEqual("/**;/name[ppp*]/a", get_subtopic('/**;/name[ppp*]/**', 'a'))
        self.assertEqual("/**;/name[ppp*]/*;", get_subtopic('/**;/name[ppp*]/*;', 'a'))

        # wildcard with ;
        self.assertEqual("/*;", get_subtopic('/*;', 'a'))
        self.assertEqual("/**;", get_subtopic('/**;', 'a'))
        self.assertEqual("/*;/a", get_subtopic('/*;/*', 'a'))
        self.assertEqual("/*;/a", get_subtopic('/*;/**', 'a'))
        self.assertEqual("/*;/*;", get_subtopic('/*;/*;', 'a'))
        self.assertEqual("/*;/**;", get_subtopic('/*;/**;', 'a'))

