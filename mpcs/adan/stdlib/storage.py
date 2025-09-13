import sqlite3
import os
import json
from typing import Optional

default_db_path = os.path.join(os.getcwd(), "..", "..", "data", "dbs", "kv.db")
print("default: ", default_db_path)

def _ensure_db(db_path: str = default_db_path):
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS kv (
                key   TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        conn.commit()

def _put( key: str, value: str):
    _ensure_db()
    with sqlite3.connect(default_db_path) as conn:
        conn.execute(
            "INSERT INTO kv(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )
        conn.commit()

def _get(key: str) -> Optional[str]:
    _ensure_db(default_db_path)
    with sqlite3.connect(default_db_path) as conn:
        cur = conn.execute("SELECT value FROM kv WHERE key=?", (key,))
        row = cur.fetchone()
        return None if row is None else row[0]

def _delete(key: str) -> bool:
    _ensure_db(default_db_path)
    with sqlite3.connect(default_db_path) as conn:
        cur = conn.execute("DELETE FROM kv WHERE key=?", (key,))
        conn.commit()
        return cur.rowcount > 0  # True si eliminó algo

def _list(prefix: str, limit: int, start_after: Optional[str]):
    _ensure_db(default_db_path)
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

    with sqlite3.connect(default_db_path) as conn:
        cur = conn.execute(sql, tuple(params))
        rows = cur.fetchall()

    has_more = len(rows) > limit
    rows = rows[:limit]
    next_start_after = rows[-1][0] if has_more else None
    items = [{"key": k, "value": v} for (k, v) in rows]
    return {"items": items, "next_start_after": next_start_after, "has_more": has_more}

def register(mcp, config):

    @mcp.tool
    def put(key: str, value: str) -> str:
        """put an entry in the storage system in a json format with the provided key"""
        try:
            _put(key, value)
            return f"✔️ put key='{key}'"
        except Exception as e:
            return f"❌ put error: {e}"

    @mcp.tool
    def get(key: str) -> str:
        """get an entry from the storage system in a json format with the provided key"""
        try:
            val = _get(key)
            return json.dumps({"found": val is not None, "value": val}, ensure_ascii=False)
        except Exception as e:
            return f"❌ get error: {e}"

    @mcp.tool
    def delete(key: str) -> str:
        """delete an entry from the storage system with the provided key"""
        try:
            deleted = _delete( key)
            if deleted:
                return f"✔️ delete key='{key}'"
            else:
                return f"⚠️ key='{key}' not found"
        except Exception as e:
            return f"❌ delete error: {e}"

    @mcp.tool
    def list(prefix: str = "", limit: int = 100, start_after: str | None = None) -> str:
        """list pairs of (key,value) ordered by key in ascendent order. pagination works with start_after"""
        try:
            out = _list(prefix, max(1, min(limit, 1000)), start_after)
            return json.dumps(out, indent=2, ensure_ascii=False)
        except Exception as e:
            return f"❌ list error: {e}"
