import pathlib
import pytest
from typing import Callable, Optional

THIS_DIR = pathlib.Path(__file__).parent


@pytest.fixture
def dyn_method(request):
    signature = request.param
    context = globals().copy()
    exec(f"def dynamic_method({signature}): pass", context)

    return context['dynamic_method']


@pytest.fixture
def resources():
    def getter(name: str, loader: Optional[Callable] = None) -> str:
        resource_file = THIS_DIR / 'resources' / name
        data = resource_file.read_text()
        if loader:
            return loader(data)
        else:
            return data

    return getter
