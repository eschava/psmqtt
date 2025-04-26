# Copyright (c) 2016 psmqtt project
# Licensed under the MIT License.  See LICENSE file in the project root for full license information.

from typing import Tuple

class Topic:
    def __init__(self, topic:str):

        # sanitize topic name by removing any empty topic-level separators:
        topic = topic.replace('//', '/')

        self.topic = topic
        self.wildcard_index, self.wildcard_len = self._find_wildcard(topic)
        return

    @staticmethod
    def _find_wildcard(topic:str) -> Tuple[int, int]:
        start = 0
        # search for * or ** (but not *; or **;) outside of []
        while start < len(topic):
            wildcard_index = topic.find('*', start)
            if wildcard_index < 0:
                break
            bracket_index = topic.find('[', start)
            if 0 <= bracket_index < wildcard_index:
                start = topic.find(']', bracket_index)
                continue
            wildcard_len = 1
            if wildcard_index + 1 < len(topic) and topic[wildcard_index + 1] == '*':  # ** sequence
                wildcard_len += 1
            if wildcard_index + wildcard_len < len(topic) and topic[wildcard_index + wildcard_len] == ';':
                start = wildcard_index + wildcard_len
                continue
            return wildcard_index, wildcard_len
        return -1, -1

    def is_multitopic(self) -> bool:
        return self.wildcard_index > 0

    def get_subtopic(self, param:str) -> str:
        if self.wildcard_index < 0:
            raise Exception(f"Topic {self.topic} has no wildcard")
        subtopic = self.topic[:self.wildcard_index] + param + self.topic[self.wildcard_index + self.wildcard_len:]
        # ensure no empty topic-level separators are present:
        return subtopic.replace("//", "/")

    def get_topic(self) -> str:
        return self.topic

    def get_error_topic(self) -> str:
        return self.topic + "/error"
