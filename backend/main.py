try:  # package import: python -m uvicorn backend.main:app
    from .nanus_backend.api import app, create_app
except ImportError:  # direct import with backend/ on PYTHONPATH
    from nanus_backend.api import app, create_app

__all__ = ["app", "create_app"]
