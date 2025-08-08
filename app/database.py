import psycopg
from psycopg_pool import ConnectionPool
from config import DB_CONFIG  # This is safe now

class Database:
    _pool = None

    @classmethod
    def initialize(cls):
        """Call this explicitly in your app startup"""
        cls._pool = ConnectionPool(
            conninfo=DB_CONFIG['DATABASE_URL'],
            min_size=DB_CONFIG['POOL_MIN'],
            max_size=DB_CONFIG['POOL_MAX'],
            open=False
        )
        cls._pool.open()
        cls._pool.wait()

    @classmethod
    def get_connection(cls):
        """Get a connection from the pool"""
        return cls._pool.getconn()

    @classmethod
    def return_connection(cls, conn):
        """Return connection to the pool"""
        cls._pool.putconn(conn)

    @classmethod
    def execute_query(cls, query, params=None, fetch=True):
        """Execute a query with connection pooling"""
        conn = cls.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(query, params)
                if fetch:
                    if cur.description:  # If it's a SELECT
                        columns = [desc.name for desc in cur.description]
                        return [dict(zip(columns, row)) for row in cur.fetchall()]
                    return cur.fetchone()
                conn.commit()
        finally:
            cls.return_connection(conn)