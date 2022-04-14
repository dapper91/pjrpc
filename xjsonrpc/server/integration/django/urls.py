import itertools
from .sites import jsonrpc_sites

urlpatterns = list(itertools.chain.from_iterable((site.urls for site in jsonrpc_sites)))
