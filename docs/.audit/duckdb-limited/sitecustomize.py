import duckdb

_original_connect = duckdb.connect


def _bounded_connect(*args, **kwargs):
    settings = dict(kwargs.get("config") or {})
    settings.setdefault("memory_limit", "8GB")
    kwargs["config"] = settings
    return _original_connect(*args, **kwargs)


duckdb.connect = _bounded_connect
