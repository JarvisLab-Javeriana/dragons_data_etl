
from __future__ import annotations

import logging

import certifi
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.errors import PyMongoError

from src.gdelt.common.config import MongoDBConfig
from src.gdelt.common.exceptions import MongoDBError

logger = logging.getLogger(__name__)


class MongoDBConnection:
    """Wraps a single `MongoClient` + selected `Database`."""

    def __init__(self, config: MongoDBConfig) -> None:
        self.config = config
        self._client: MongoClient | None = None

    @property
    def client(self) -> MongoClient:
        if self._client is None:
            try:
                client_kwargs: dict = {
                    "connectTimeoutMS": self.config.connect_timeout_ms,
                    "serverSelectionTimeoutMS": self.config.server_selection_timeout_ms,
                }
                # Atlas (mongodb+srv) needs an explicit CA bundle on some
                # Windows/OpenSSL combinations; local mongodb:// stays as-is.
                if self.config.uri.startswith("mongodb+srv://"):
                    client_kwargs["tls"] = True
                    client_kwargs["tlsCAFile"] = certifi.where()
                    # Avoid OCSP stapling failures that surface as TLS alerts
                    # on some Windows/OpenSSL 3.x + Atlas combinations.
                    client_kwargs["tlsDisableOCSPEndpointCheck"] = True
                self._client = MongoClient(self.config.uri, **client_kwargs)
                # Force a round-trip so connection errors surface early
                # instead of on the first real query.
                self._client.admin.command("ping")
                logger.info("Connected to MongoDB database '%s'", self.config.database)
            except PyMongoError as exc:
                raise MongoDBError(f"Failed to connect to MongoDB: {exc}") from exc
        return self._client

    @property
    def database(self) -> Database:
        return self.client[self.config.database]

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self) -> "MongoDBConnection":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def get_server_stats(self) -> dict:
        """Used by monitoring to report collection/storage sizes
        (see project spec section 13)."""
        try:
            return self.database.command("dbStats")
        except PyMongoError as exc:
            raise MongoDBError(f"Failed to fetch MongoDB dbStats: {exc}") from exc
