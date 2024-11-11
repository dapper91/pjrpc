import uuid
from typing import Any

import pydantic

import pjrpc.server
import pjrpc.server.specs.extractors.pydantic
from pjrpc.server.specs import extractors
from pjrpc.server.specs import openapi as specs


class JSONEncoder(pjrpc.server.JSONEncoder):
    def default(self, o: Any) -> Any:
        if isinstance(o, pydantic.BaseModel):
            return o.model_dump()
        if isinstance(o, uuid.UUID):
            return str(o)

        return super().default(o)


spec = specs.OpenAPI(
    info=specs.Info(version="1.0.0", title="User storage"),
    servers=[
        specs.Server(
            url='http://127.0.0.1:8000',
        ),
    ],
    schema_extractor=extractors.pydantic.PydanticSchemaExtractor(),
    ui=specs.SwaggerUI(),
)
