import os

import libsql_client

_client = None


def get_client():
    global _client
    if _client is None:
        url = os.environ["TURSO_DATABASE_URL"]
        # Force HTTP transport (websocket/hrana handshakes are unreliable in some
        # network environments); libsql:// -> https:// gives the same database.
        if url.startswith("libsql://"):
            url = "https://" + url[len("libsql://") :]
        _client = libsql_client.create_client_sync(
            url=url,
            auth_token=os.environ["TURSO_AUTH_TOKEN"],
        )
    return _client


def execute(sql, args=None):
    return get_client().execute(sql, args or [])


def batch(statements):
    """statements: list of (sql, args) tuples, run as a single transaction."""
    return get_client().batch(statements)


def close_client():
    global _client
    if _client is not None:
        _client.close()
        _client = None
