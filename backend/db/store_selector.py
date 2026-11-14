"""Chooses the workspace store in one place.

WORKSPACE_BACKEND picks it:

    sqlite    (default) services/store.py, the prototype's local snapshot store
    postgres  db/repository.py, the schema v2 tables through SQLModel
              (needs DATABASE_URL; see db/database.py)

Routes import the selected store instead of importing a store directly:

    from db.store_selector import store

With the default the object is the services.store module itself, so the
current behaviour (and tests that patch store.DB_PATH) are unchanged. Both
modules offer atomic(), create_change(), issue_client_token(),
change_for_token(), work_order(), notify() and add_event(); only the
repository also has the query and decision functions the routes currently do
inline against store.CHANGES (see the B3 pull request description).
"""

import os
from importlib import import_module
from types import ModuleType

BACKENDS = {"sqlite": "services.store", "postgres": "db.repository"}
DEFAULT_BACKEND = "sqlite"


def backend_name() -> str:
    name = (os.environ.get("WORKSPACE_BACKEND") or DEFAULT_BACKEND).strip().lower()
    if name not in BACKENDS:
        raise RuntimeError(
            f"WORKSPACE_BACKEND must be one of {', '.join(BACKENDS)}; got {name!r}."
        )
    return name


def load_store(name: str | None = None) -> ModuleType:
    """Import and return the store module for a backend name (default: the setting)."""
    return import_module(BACKENDS[name or backend_name()])


# Resolved when this module is first imported, so a bad value fails at start-up.
store = load_store()
