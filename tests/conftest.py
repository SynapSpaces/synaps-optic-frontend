import json

import pytest
from jinja2 import Environment, FileSystemLoader, select_autoescape

from optic_frontend import TEMPLATES_DIR


@pytest.fixture
def jinja_env() -> Environment:
    """Mirror the backend's Jinja2 setup: the templates dir plus the fromjson filter."""
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html"]),
    )
    env.filters["fromjson"] = json.loads
    return env
