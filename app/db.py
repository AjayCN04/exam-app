import os
import time

import libsql_client

_client = None

_MAX_ATTEMPTS = 4
_RETRY_DELAY_SECONDS = 1


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
    # The HTTP transport occasionally drops a response mid-batch of many sequential
    # calls (surfaces as a KeyError in libsql_client rather than a clean network
    # error) — retry a few times before giving up, since a bulk import can make
    # thousands of round trips and a single blip shouldn't abort the whole run.
    last_error = None
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        try:
            return get_client().execute(sql, args or [])
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt < _MAX_ATTEMPTS:
                time.sleep(_RETRY_DELAY_SECONDS * attempt)
    raise last_error


def batch(statements):
    """statements: list of (sql, args) tuples, run as a single transaction."""
    return get_client().batch(statements)


def close_client():
    global _client
    if _client is not None:
        _client.close()
        _client = None
