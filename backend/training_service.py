from fastapi import FastAPI

from app.api.routes import training
from app.core.config import get_settings
from app.core.logging import configure_logging

settings = get_settings()
configure_logging(settings.log_level)

app = FastAPI(title='Training Service', version=settings.app_version)


@app.get('/api/health')
def health():
    return {'ok': True, 'service': 'training'}


app.include_router(training.router, prefix='/api')
