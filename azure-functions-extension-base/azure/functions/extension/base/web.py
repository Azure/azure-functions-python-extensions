from abc import abstractmethod
from enum import Enum
from typing import Callable

base_extension_module = __name__


# Base extension pkg
class ModuleTrackerMeta(type):
    _module = None

    def __new__(cls, name, bases, dct, **kwargs):
        new_class = super().__new__(cls, name, bases, dct)
        new_module = dct.get('__module__')
        if new_module != base_extension_module:
            if cls._module is None:
                cls._module = new_module
            elif cls._module != new_module:
                raise Exception(f'Only one web extension package shall be imported, '
                                f'{cls._module} and {new_module} are imported')
        return new_class

    @classmethod
    def get_module(cls):
        return cls._module

    @classmethod
    def module_imported(cls):
        return cls._module is not None


class RequestTrackerMeta(type):
    _request_type = None

    def __new__(cls, name, bases, dct, **kwargs):
        new_class = super().__new__(cls, name, bases, dct)

        request_type = dct.get('request_type')

        if request_type is None:
            raise Exception(f'Request type not provided for class {name}')

        if cls._request_type is not None:
            raise Exception(f'Only one request type shall be recorded for class {name} '
                            f'but found {cls._request_type} and {request_type}')
        cls._request_type = request_type

        return new_class

    @classmethod
    def get_request_type(cls):
        return cls._request_type

    @classmethod
    def check_type(cls, pytype: type) -> bool:
        return cls._request_type is not None and issubclass(pytype, cls._request_type)


class ResponseTrackerMeta(type):
    _response_types = {}

    def __new__(cls, name, bases, dct, **kwargs):
        new_class = super().__new__(cls, name, bases, dct)

        label = dct.get('label')
        response_type = dct.get('response_type')

        if label is None:
            raise Exception(f'Response label not provided for class {name}')
        if response_type is None:
            raise Exception(f'Response type not provided for class {name}')
        if cls._response_types.get(label) is not None:
            raise Exception(f'Only one response type shall be recorded for class {name} '
                            f'but found {cls._response_types.get(label)} and {response_type}')

        cls._response_types[label] = response_type

        return new_class

    @classmethod
    def get_standard_response_type(cls):
        return cls.get_response_type(ResponseLabels.STANDARD)

    @classmethod
    def get_response_type(cls, label):
        return cls._response_types.get(label)

    @classmethod
    def check_type(cls, pytype: type) -> bool:
        return cls._response_types is not None and any(issubclass(pytype, response_type)
                                                       for response_type in cls._response_types.values())


class WebApp(metaclass=ModuleTrackerMeta):
    @abstractmethod
    def route(self, func: Callable):
        pass

    @abstractmethod
    def get_app(self):
        pass


class WebServer(metaclass=ModuleTrackerMeta):
    def __init__(self, hostname, port, web_app: WebApp):
        self.hostname = hostname
        self.port = port
        self.web_app = web_app.get_app()

    @abstractmethod
    async def serve(self):
        pass


def http_v2_enabled() -> bool:
    return ModuleTrackerMeta.module_imported()


class ResponseLabels(Enum):
    STANDARD = 'standard'
    STREAMING = 'streaming'
    FILE = 'file'
    HTML = 'html'
    JSON = 'json'
    ORJSON = 'orjson'
    PLAIN_TEXT = 'plain_text'
    REDIRECT = 'redirect'
    UJSON = 'ujson'
