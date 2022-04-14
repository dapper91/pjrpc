import uuid
from typing import Any

import pydantic
import xjsonrpc.server
import xjsonrpc.server.specs.extractors.pydantic
from xjsonrpc.server.specs import extractors, openapi as specs


class JSONEncoder(xjsonrpc.server.JSONEncoder):
    def default(self, o: Any) -> Any:
        if isinstance(o, pydantic.BaseModel):
            return o.dict()
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
