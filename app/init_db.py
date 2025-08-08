from database import Database

def drop_tables():
    """Drop existing tables if they exist"""
    Database.execute_query(
        """
        DROP TABLE IF EXISTS transactions CASCADE;
        """,
        fetch=False
    )
    print("Dropped existing tables")

def create_tables():
    """Create fresh tables with all constraints"""
    Database.execute_query(
        """
        CREATE TABLE transactions (
            id SERIAL PRIMARY KEY,
            tckr VARCHAR(10) NOT NULL,
            current_price NUMERIC(12,4) NOT NULL,
            quantity INTEGER NOT NULL,
            average_cost NUMERIC(12,4) NOT NULL,
            profit NUMERIC(12,4),
            buy_date TIMESTAMPTZ DEFAULT NOW(),
            sell_date TIMESTAMPTZ,
            sell_reason VARCHAR(50),
            target_price NUMERIC(12,4) NOT NULL,
            pre_dip_price NUMERIC(12,4) NOT NULL,
            week52_low NUMERIC(12,4) NOT NULL,
            week52_high NUMERIC(12,4) NOT NULL,
            pre_dip_percentile NUMERIC(5,2) NOT NULL,
            strategy_version VARCHAR(20)
        );
        """,
        fetch=False
    )

    Database.execute_query(
        """
        CREATE INDEX idx_transactions_active 
        ON transactions(tckr) WHERE sell_date IS NULL;
        """,
        fetch=False
    )
    print("Created new tables")

if __name__ == "__main__":
    try:
        Database.initialize()
        drop_tables()  # First drop existing tables
        create_tables()  # Then create fresh ones
    finally:
        if hasattr(Database, '_pool') and Database._pool:
            Database._pool.close()