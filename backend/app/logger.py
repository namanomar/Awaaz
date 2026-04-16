from app.db import log_call, init_db

init_db()   # idempotent — safe to call on every startup

__all__ = ["log_call"]
