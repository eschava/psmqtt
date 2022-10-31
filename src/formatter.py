from typing import Any, Optional, Text, Tuple
from jinja2 import Environment  # pip install jinja2

from . import filters


class Formatter:
    '''
    '''
    env:Optional[Environment] = None

    @classmethod
    def get_format(cls, path:str) -> Tuple[str, Optional[str]]:
        '''
        Tuple would be a better choice for typing
        '''
        i = path.find("{{")
        if i > 0:
            i = path.rfind("/", 0, i)
            if i > 0:
                return (path[0:i], path[i+1:])
        return (path, None)

    @classmethod
    def format(cls, f:str, value: Any) -> Text:
        env = cls.get_environment()
        return env.from_string(f).render(value if isinstance(value, dict) else {"x": value})

    @classmethod
    def get_environment(cls) -> Environment:
        if cls.env is None:
            cls.env = Environment()
            filters.register_filters(cls.env)

        return cls.env
