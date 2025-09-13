import sqlite3
import os
import json
from typing import Optional

def _ensure_db(db_path: str):
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS kv (
                key   TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        conn.commit()

def _put(db_path: str, key: str, value: str):
    _ensure_db(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO kv(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )
        conn.commit()

def _get(db_path: str, key: str) -> Optional[str]:
    _ensure_db(db_path)
    with sqlite3.connect(db_path) as conn:
        cur = conn.execute("SELECT value FROM kv WHERE key=?", (key,))
        row = cur.fetchone()
        return None if row is None else row[0]

def _list(db_path: str, prefix: str, limit: int, start_after: Optional[str]):
    _ensure_db(db_path)
    params = []
    where = "WHERE 1=1"
    if prefix:
        where += " AND key LIKE ?"
        params.append(prefix + "%")
    if start_after:
        where += " AND key > ?"
        params.append(start_after)

    sql = f"""
        SELECT key, value
        FROM kv
        {where}
        ORDER BY key ASC
        LIMIT ?
    """
    params.append(limit + 1)  # pedir 1 extra para saber si hay más

    with sqlite3.connect(db_path) as conn:
        cur = conn.execute(sql, tuple(params))
        rows = cur.fetchall()

    has_more = len(rows) > limit
    rows = rows[:limit]
    next_start_after = rows[-1][0] if has_more else None
    items = [{"key": k, "value": v} for (k, v) in rows]
    return {"items": items, "next_start_after": next_start_after, "has_more": has_more}

def register(mcp, config):

    @mcp.tool
    def put(key: str, value: str, db_path: str = "kv.db") -> str:
        """put an entry in the storage system in a json format with the provided key"""
        try:
            _put(db_path, key, value)
            return f"✔️ put key='{key}'"
        except Exception as e:
            return f"❌ put error: {e}"

    @mcp.tool
    def get(key: str, db_path: str = "kv.db") -> str:
        """get an entry from the storage system in a json format with the provided key"""
        try:
            val = _get(db_path, key)
            return json.dumps({"found": val is not None, "value": val}, ensure_ascii=False)
        except Exception as e:
            return f"❌ get error: {e}"

    @mcp.tool
    def list(prefix: str = "", limit: int = 100, start_after: str | None = None, db_path: str = "kv.db") -> str:
        """list pairs of (key,value) ordered by key in ascendent order. pagination works with start_after"""
        try:
            out = _list(db_path, prefix, max(1, min(limit, 1000)), start_after)
            return json.dumps(out, indent=2, ensure_ascii=False)
        except Exception as e:
            return f"❌ list error: {e}"
