from typing import Tuple, Dict

class Topic:
    def __init__(self, topic:str):
        self.topic = topic
        self.wildcard_index, self.wildcard_len = self._find_wildcard(topic)
        return

    @classmethod
    def from_task(cls, topic_prefix: str, task: Dict[str,str]) -> 'Topic':
        # create the MQTT topic by concatenating the task name and its parameters with the MQTT topic-level separator '/'
        topicName = topic_prefix + task["task"]
        nonEmptyParams = [x for x in task["params"] if x != '']

        escapedParams = []
        for x in nonEmptyParams:
            if isinstance(x,str):
                escapedParams.append(x.replace('/', '|'))
            elif isinstance(x,int):
                escapedParams.append(str(x))
        if len(escapedParams) > 0:
            topicName += '/' + '/'.join(escapedParams)
        return Topic(topicName)

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
        return self.topic[:self.wildcard_index] + param + self.topic[self.wildcard_index + self.wildcard_len:]

    def get_topic(self) -> str:
        return self.topic

    def get_error_topic(self) -> str:
        return self.topic + "/error"
