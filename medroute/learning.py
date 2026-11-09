"""Local reviewer preferences, restricted to equivalent valid proposals."""
from contextlib import closing
import hashlib
import json
import logging
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / 'runtime' / 'review_preferences.sqlite3'


def context_key(known, alternatives):
    value = {'known': known, 'valid': [x['method'] for x in alternatives if x['operational_pass']]}
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def preferences(context):
    try:
        if not DB_PATH.exists():
            return {}
        with closing(sqlite3.connect(DB_PATH.resolve().as_uri() + '?mode=ro',
                                     uri=True, timeout=1)) as database:
            rows = database.execute('SELECT method, useful FROM preferences WHERE context=?', (context,))
            return {method: useful for method, useful in rows
                    if method in ('local_only', 'greedy', 'optimized')
                    and type(useful) is int and useful in (-1, 1)}
    except (OSError, sqlite3.Error):
        logging.getLogger(__name__).warning('Local preferences unavailable; using scenario scores.')
        return {}


def save_preference(context, method, useful):
    if method not in ('local_only', 'greedy', 'optimized') or type(useful) is not bool:
        raise ValueError('Invalid preference.')
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(DB_PATH)) as database:
        database.execute('CREATE TABLE IF NOT EXISTS preferences (context TEXT, method TEXT, useful INTEGER, PRIMARY KEY(context,method))')
        database.execute('INSERT INTO preferences VALUES (?,?,?) ON CONFLICT(context,method) DO UPDATE SET useful=excluded.useful',
                         (context, method, 1 if useful else -1))
        database.commit()
