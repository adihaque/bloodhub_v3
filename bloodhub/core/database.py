import os
import math
import sqlite3
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional, Type
from bloodhub.core.config import settings

def sqlite_haversine(lat1, lon1, lat2, lon2):
    """Calculates haversine distance in kilometers directly in SQLite queries."""
    try:
        if None in (lat1, lon1, lat2, lon2):
            return 999999.0
        lat1, lon1, lat2, lon2 = float(lat1), float(lon1), float(lat2), float(lon2)
        R = 6371.0
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return round(R * c, 3)
    except Exception:
        return 999999.0

def _probe_sqlite_path(path: str) -> bool:
    try:
        dir_name = os.path.dirname(path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        probe_conn = sqlite3.connect(path, timeout=3.0)
        probe_conn.execute("CREATE TABLE IF NOT EXISTS _fs_probe (id INT);")
        probe_conn.execute("DROP TABLE _fs_probe;")
        probe_conn.close()
        return True
    except Exception:
        return False

def get_db_path() -> str:
    """
    Resolves the persistent SQLite database path based on the environment:
    - pilot: data/bloodhub_pilot.db (with sandbox fallback)
    - development: data/bloodhub_dev.db
    - test: /tmp/bloodhub_test.db
    """
    env = settings.ENVIRONMENT.lower()
    
    # 1. If explicit URL provided
    if settings.DATABASE_URL:
        raw_path = settings.DATABASE_URL.replace("sqlite:///", "")
        if _probe_sqlite_path(raw_path):
            return raw_path
        # Sandbox 9p fallback if requested directory fails file-locking
        fallback = f"/tmp/bloodhub_{env}.db"
        return fallback

    # 2. Environment default
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    data_dir = os.path.join(base_dir, "data")
    
    if env == "test":
        return f"/tmp/bloodhub_test.db"
    elif env == "development":
        primary_path = os.path.join(data_dir, "bloodhub_dev.db")
    else:  # 'pilot' or real-user mode
        primary_path = os.path.join(data_dir, "bloodhub_pilot.db")

    if _probe_sqlite_path(primary_path):
        return primary_path

    # Fallback to local overlayfs /tmp if working directory is mounted over 9p
    fallback = f"/tmp/bloodhub_{env}.db"
    return fallback

def create_connection() -> sqlite3.Connection:
    path = get_db_path()
    conn = sqlite3.connect(path, timeout=30.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.create_function("haversine", 4, sqlite_haversine)
    return conn

def backup_database(destination_path: Optional[str] = None) -> str:
    """Performs a portable, consistent SQL dump backup."""
    src_conn = create_connection()
    if not destination_path:
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        backup_dir = os.path.join(base_dir, "backups")
        os.makedirs(backup_dir, exist_ok=True)
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        destination_path = os.path.join(backup_dir, f"bloodhub_backup_{settings.ENVIRONMENT}_{ts}.sql")
    
    dir_name = os.path.dirname(destination_path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)

    with open(destination_path, "w", encoding="utf-8") as f:
        for line in src_conn.iterdump():
            f.write(line + chr(10))
    src_conn.close()
    return destination_path

class QueryBuilder:
    def __init__(self, session: "DatabaseSession", model_cls: Type["BaseModel"]):
        self.session = session
        self.model_cls = model_cls
        self.where_clauses: List[str] = []
        self.params: List[Any] = []
        self._order_by: Optional[str] = None
        self._limit: Optional[int] = None

    def filter(self, clause: Any, *args):
        if isinstance(clause, str):
            self.where_clauses.append(clause)
            if args:
                if len(args) == 1 and isinstance(args[0], (list, tuple)):
                    self.params.extend(args[0])
                else:
                    self.params.extend(args)
        return self

    def filter_by(self, **kwargs):
        for k, v in kwargs.items():
            self.where_clauses.append(f"{k} = ?")
            self.params.append(v)
        return self

    def with_for_update(self):
        return self

    def order_by(self, clause: str):
        self._order_by = clause
        return self

    def limit(self, count: int):
        self._limit = count
        return self

    def _build_sql(self, select_fields: str = "*") -> str:
        sql = f"SELECT {select_fields} FROM {self.model_cls.__tablename__}"
        if self.where_clauses:
            sql += " WHERE " + " AND ".join(self.where_clauses)
        if self._order_by:
            sql += f" ORDER BY {self._order_by}"
        if self._limit is not None:
            sql += f" LIMIT {self._limit}"
        return sql

    def all(self) -> List[Any]:
        sql = self._build_sql()
        rows = self.session.execute_raw(sql, self.params).fetchall()
        return [self.model_cls.from_row(row, self.session) for row in rows]

    def first(self) -> Optional[Any]:
        old_limit = self._limit
        self._limit = 1
        rows = self.all()
        self._limit = old_limit
        return rows[0] if rows else None

    def count(self) -> int:
        sql = self._build_sql(select_fields="COUNT(*)")
        cur = self.session.execute_raw(sql, self.params)
        res = cur.fetchone()
        return res[0] if res else 0

    def delete(self):
        sql = f"DELETE FROM {self.model_cls.__tablename__}"
        if self.where_clauses:
            sql += " WHERE " + " AND ".join(self.where_clauses)
        self.session.execute_raw(sql, self.params)

class DatabaseSession:
    def __init__(self):
        self.conn = create_connection()
        self.pending_adds: List["BaseModel"] = []
        self.is_closed = False

    def execute_raw(self, sql: str, params: Optional[List[Any]] = None):
        cur = self.conn.cursor()
        cur.execute(sql, params or [])
        return cur

    def execute(self, sql: str, params: Optional[List[Any]] = None):
        return self.execute_raw(sql, params)

    def query(self, model_cls: Type["BaseModel"]) -> QueryBuilder:
        return QueryBuilder(self, model_cls)

    def add(self, entity: "BaseModel"):
        entity._session = self
        if entity not in self.pending_adds:
            self.pending_adds.append(entity)

    def delete(self, entity: "BaseModel"):
        if hasattr(entity, "id") and entity.id:
            sql = f"DELETE FROM {entity.__tablename__} WHERE id = ?"
            self.execute_raw(sql, [entity.id])

    def flush(self):
        for entity in self.pending_adds:
            entity._save(self)
        self.pending_adds.clear()

    def commit(self):
        self.flush()
        self.conn.commit()

    def rollback(self):
        self.pending_adds.clear()
        self.conn.rollback()

    def refresh(self, entity: "BaseModel"):
        if hasattr(entity, "id") and entity.id:
            sql = f"SELECT * FROM {entity.__tablename__} WHERE id = ?"
            row = self.execute_raw(sql, [entity.id]).fetchone()
            if row:
                for k in row.keys():
                    setattr(entity, k, row[k])

    def close(self):
        if not self.is_closed:
            try:
                self.conn.close()
            except Exception:
                pass
            self.is_closed = True

def get_db():
    session = DatabaseSession()
    try:
        yield session
    finally:
        session.close()

def SessionLocal() -> DatabaseSession:
    return DatabaseSession()

class _Base:
    pass

Base = _Base()
engine = object()
