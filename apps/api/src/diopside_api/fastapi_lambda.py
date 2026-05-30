from __future__ import annotations

from mangum import Mangum

from .fastapi_app import create_app


app = create_app()
lambda_handler = Mangum(app, lifespan="off")
