import yfinance as yf
import requests
from datetime import datetime
from database import Database
from config import FMP_API_KEY
import json

class TradingStrategy:
    def __init__(self, investment_per_trade=2000, percentile_threshold=50):
        self.investment_per_trade = investment_per_trade
        self.percentile_threshold = percentile_threshold

    def get_intraday_losers(self):
        """Get intraday losers from FMP API with better error handling"""
        url = f"https://financialmodelingprep.com/api/v3/stock_market/losers?apikey={FMP_API_KEY}"
        print(url)
        try:
            response = requests.get(url)
            response.raise_for_status()  # Raises an HTTPError for bad responses
            
            # Try to parse the response
            data = response.json()
            
            # Verify the response structure
            if not isinstance(data, list):
                raise ValueError("Unexpected API response format")
                
            return [
                {
                    'symbol': stock['symbol'],
                    'price': float(stock['price']),
                    'pre_dip_price': float(stock['price']) / (1 + float(stock['changesPercentage'])/100)
                }
                for stock in data
                if all(key in stock for key in ['symbol', 'price', 'changesPercentage'])
            ]
            
        except Exception as e:
            print(f"Error fetching intraday losers: {str(e)}")
            print(f"API Response: {response.text if 'response' in locals() else 'No response'}")
            return []

    def run_strategy(self, execute_trades=False, strategy_version="v1.0"):
        results = {"buys": [], "sells": []}
        
        try:
            # Buy Strategy
            losers = self.get_intraday_losers()
            if not losers:
                print("No valid intraday losers found")
                return results
                
            for stock in losers:
                try:
                    ticker = stock['symbol']
                    stock_data = yf.Ticker(ticker)
                    
                    hist = stock_data.history(period="1y")
                    
                    if hist.empty:
                        print(f"No history data for {ticker}")
                        continue
                    print(stock_data)  
                    target_price = stock_data.info.get('targetMeanPrice')
                    if not target_price:
                        print(f"No target price for {ticker}")
                        continue
                    
                    week52_high = hist['High'].max()
                    week52_low = hist['Low'].min()
                    pre_dip_percentile = (stock['pre_dip_price'] - week52_low) / (week52_high - week52_low) * 100
                    
                    if (pre_dip_percentile >= self.percentile_threshold and 
                        stock['price'] < target_price):
                        
                        quantity = int(self.investment_per_trade / stock['price'])
                        
                        if execute_trades:
                            Database.execute_query(
                                """
                                INSERT INTO transactions 
                                (tckr, current_price, quantity, average_cost, target_price,
                                pre_dip_price, week52_low, week52_high, pre_dip_percentile, strategy_version)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                """,
                                (ticker, stock['price'], quantity, stock['price'], target_price,
                                stock['pre_dip_price'], week52_low, week52_high, pre_dip_percentile, strategy_version),
                                fetch=False
                            )
                            results["buys"].append(ticker)
                            
                except Exception as e:
                    print(f"Error processing stock {stock.get('symbol', 'unknown')}: {str(e)}")
                    continue
            
            # Sell Strategy
            active_positions = Database.execute_query(
                "SELECT id, tckr, quantity, average_cost, target_price FROM transactions WHERE sell_date IS NULL"
            )
            
            for pos in active_positions:
                try:
                    current_price = yf.Ticker(pos['tckr']).history(period='1d')['Close'].iloc[-1]
                    if current_price >= pos['target_price']:
                        profit = (current_price - pos['average_cost']) * pos['quantity']
                        
                        if execute_trades:
                            Database.execute_query(
                                """
                                UPDATE transactions 
                                SET current_price = %s, profit = %s, sell_date = %s, sell_reason = 'TARGET_REACHED'
                                WHERE id = %s
                                """,
                                (current_price, profit, datetime.utcnow(), pos['id']),
                                fetch=False
                            )
                            results["sells"].append(pos['tckr'])
                            
                except Exception as e:
                    print(f"Error processing position {pos.get('tckr', 'unknown')}: {str(e)}")
                    continue
                    
        except Exception as e:
            print(f"Strategy execution failed: {str(e)}")
            raise  # Re-raise the exception for the API to handle
            
        return results