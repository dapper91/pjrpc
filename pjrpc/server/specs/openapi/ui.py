import functools as ft
import pathlib
import re
from typing import Any

import openapi_ui_bundles

from pjrpc.server.specs import BaseUI


class SwaggerUI(BaseUI):
    """
    Swagger UI.

    :param config: documentation configurations
                   (see https://github.com/swagger-api/swagger-ui/blob/master/docs/usage/configuration.md).
    """

    def __init__(self, **configs: Any):
        self._configs = configs
        self._static_folder = pathlib.Path(openapi_ui_bundles.swagger_ui.static_path)

    def get_static_folder(self) -> pathlib.Path:
        return self._static_folder

    @ft.lru_cache
    def get_index_page(self, spec_url: str) -> str:
        index_path = self.get_static_folder() / 'index.html'
        index_page = index_path.read_text()

        config = dict(self._configs, **{'url': spec_url, 'dom_id': '#swagger-ui'})
        config_str = ', '.join(f'{param}: "{value}"' for param, value in config.items())

        return re.sub(
            pattern=r'SwaggerUIBundle\({.*?}\)',
            repl=f'SwaggerUIBundle({{ {config_str} }})',
            string=index_page,
            count=1,
            flags=re.DOTALL,
        )


class RapiDoc(BaseUI):
    """
    RapiDoc UI.

    :param config: documentation configurations (see https://mrin9.github.io/RapiDoc/api.html).
                   Be aware that configuration parameters should be in snake case,
                   for example: parameter `heading-text` should be passed as `heading_text`)
    """

    def __init__(self, **configs: Any):
        self._configs = configs
        self._static_folder = pathlib.Path(openapi_ui_bundles.rapidoc.static_path)

    def get_static_folder(self) -> pathlib.Path:
        return self._static_folder

    @ft.lru_cache
    def get_index_page(self, spec_url: str) -> str:
        index_path = pathlib.Path(self.get_static_folder()) / 'index.html'
        index_page = index_path.read_text()

        config = dict(self._configs, **{'spec_url': spec_url, 'id': 'thedoc'})
        config_str = ' '.join(f'{param.replace("_", "-")}="{value}"' for param, value in config.items())

        return re.sub(
            pattern='<rapi-doc.*?>',
            repl=f'<rapi-doc {config_str}>',
            string=index_page,
            count=1,
            flags=re.DOTALL,
        )


class ReDoc(BaseUI):
    """
    ReDoc UI.

    :param config: documentation configurations (see https://github.com/Redocly/redoc#configuration).
                   Be aware that configuration parameters should be in snake case,
                   for example: parameter `heading-text` should be passed as `heading_text`)
    """

    def __init__(self, **configs: Any):
        self._configs = configs
        self._static_folder = pathlib.Path(openapi_ui_bundles.redoc.static_path)

    def get_static_folder(self) -> pathlib.Path:
        return self._static_folder

    @ft.lru_cache
    def get_index_page(self, spec_url: str) -> str:
        index_path = pathlib.Path(self.get_static_folder()) / 'index.html'
        index_page = index_path.read_text()

        config = dict(self._configs, **{'spec_url': spec_url})
        config_str = ' '.join(f'{param.replace("_", "-")}="{value}"' for param, value in config.items())

        return re.sub(
            pattern='<redoc.*?>',
            repl=f'<redoc {config_str}>',
            string=index_page,
            count=1,
            flags=re.DOTALL,
        )
