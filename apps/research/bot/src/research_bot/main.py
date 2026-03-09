from __future__ import annotations

from research_bot.api.app import create_app
from research_bot.bootstrap.settings import get_settings


app = create_app(get_settings())
