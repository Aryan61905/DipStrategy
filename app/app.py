from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from strategy import TradingStrategy
from database import Database
import uvicorn
from decimal import Decimal
from fastapi.encoders import jsonable_encoder
import json
import time

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database pool with retries
@app.on_event("startup")
async def startup_db():
    max_retries = 5
    retry_delay = 2  # seconds
    
    for attempt in range(max_retries):
        try:
            Database.initialize()
            # Verify connection works
            if Database.execute_query("SELECT 1"):
                print("Database connection established successfully")
                return
        except Exception as e:
            print(f"Database initialization attempt {attempt + 1} failed: {e}")
            if attempt == max_retries - 1:
                raise RuntimeError("Failed to initialize database after retries")
            time.sleep(retry_delay)

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)

@app.get("/api/transactions")
async def get_transactions():
    try:
        if not Database._pool:
            raise RuntimeError("Database connection not initialized")
            
        transactions = Database.execute_query(
            """SELECT 
                tckr, 
                buy_date, 
                average_cost, 
                quantity, 
                current_price, 
                target_price,
                (current_price * quantity) as value,
                profit,
                CASE WHEN sell_date IS NULL THEN 'Active' ELSE 'Closed' END as status
            FROM transactions 
            ORDER BY COALESCE(sell_date, buy_date) DESC 
            LIMIT 100"""
        )
        
        if transactions is None:
            raise ValueError("No transactions returned from database")
            
        # Convert Decimal to float and datetime to string
        for tx in transactions:
            for key, value in tx.items():
                if isinstance(value, Decimal):
                    tx[key] = float(value)
                elif hasattr(value, 'isoformat'):  # Handle datetime
                    tx[key] = value.isoformat()
        
        return JSONResponse(content=jsonable_encoder(transactions))
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            content={
                "error": "Failed to fetch transactions",
                "details": str(e)
            },
            status_code=500
        )

@app.post("/api/run-strategy")
async def run_strategy(execute: bool = True):
    try:
        if not Database._pool:
            raise RuntimeError("Database connection not initialized")
            
        strategy = TradingStrategy()
        results = strategy.run_strategy(execute_trades=execute)
        return JSONResponse(content=results)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            content={"error": str(e), "details": traceback.format_exc()},
            status_code=500
        )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)