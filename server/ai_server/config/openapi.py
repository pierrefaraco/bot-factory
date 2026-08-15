"""OpenAPI documentation setup (SpecTree + Pydantic).

Endpoints decorated with ``@api.validate(...)`` get:
- request validation against the given Pydantic model (400 on error),
- an entry in the generated OpenAPI spec.

Swagger UI is served at /api/docs/swagger/ and the raw spec at
/api/docs/openapi.json once ``api.register(app)`` has been called.
"""

from pydantic import ValidationError
from spectree import SecurityScheme, SpecTree

from ai_server.config.config import AppConfig


def pydantic_error_messages(exc: ValidationError) -> list:
    """JSON-serializable error list for manual Pydantic validation."""
    return exc.errors(include_url=False, include_context=False, include_input=False)


# Self-hosted Swagger UI page (assets in ai_server/static/swagger-ui/), so the
# docs work without internet access — SpecTree's default templates pull the UI
# from the unpkg CDN. Literal braces are doubled because SpecTree fills the
# template with str.format().
SWAGGER_PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Bot Factory API</title>
    <link rel="stylesheet" href="/static/swagger-ui/swagger-ui.css" />
</head>
<body>
    <div id="swagger-ui"></div>
    <script src="/static/swagger-ui/swagger-ui-bundle.js"></script>
    <script src="/static/swagger-ui/swagger-ui-standalone-preset.js"></script>
    <script>
    window.onload = function() {{
        SwaggerUIBundle({{
            url: "{spec_url}",
            dom_id: "#swagger-ui",
            presets: [SwaggerUIBundle.presets.apis, SwaggerUIStandalonePreset],
            layout: "StandaloneLayout",
        }});
    }};
    </script>
</body>
</html>"""

api = SpecTree(
    "flask",
    title=f"{AppConfig.APP_NAME} API",
    version=AppConfig.APP_VERSION,
    description=(
        "REST API of the Bot Factory platform: authentication, bot "
        "management, knowledge base (RAG) and token statistics. "
        "Authenticate with POST /api/auth/login, then use the returned "
        "token as 'Bearer <token>' via the Authorize button."
    ),
    path="api/docs",
    annotations=False,
    validation_error_status=400,
    page_templates={"swagger": SWAGGER_PAGE_TEMPLATE},
    security_schemes=[
        SecurityScheme(
            name="BearerAuth",
            data={"type": "http", "scheme": "bearer", "bearerFormat": "JWT"},
        )
    ],
)
