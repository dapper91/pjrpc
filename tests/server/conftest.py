import pytest


@pytest.fixture
def dyn_method(request):
    signature = request.param
    context = globals().copy()
    exec(f"def dynamic_method({signature}): pass", context)

    return context['dynamic_method']
