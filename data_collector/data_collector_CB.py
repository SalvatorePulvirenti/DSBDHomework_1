import mysql.connector
import yfinance as yf
import time

from circuit_breaker import CircuitBreaker, CircuitBreakerOpenException

DB_CONFIG ={
	'host': 'mysql',
	'user':'Admin',
	'password': '1234',
	'database': 'user_management'
}

def fetch_stock_data():
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()

    cursor.execute("SELECT email, ticker FROM users")
    users = cursor.fetchall()

    for email, ticker in users:
        try:
            stock_info = yf.Ticker(ticker).history(period="1d")
            if not stock_info.empty:
                last_price = stock_info["Close"].iloc[-1]
                last_timestamp=stock_info.index[-1]
                datatime=last_timestamp.strftime("%Y-%m-%d %H:%M:%S")
                last_price_fl=float(last_price)
                print(email,ticker,last_price,last_price_fl)
                cursor.execute("""
                    INSERT INTO stock_data (email, ticker, value,timestamp) VALUES (%s, %s, %s,%s)
                """, (email, ticker, last_price_fl,datatime))
        except Exception as e:
            print(f"Error fetching data for {ticker}: {e}")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=5)

    while True:
        try:
          result = circuit_breaker.call(fetch_stock_data)
          print(f"Call : {result}")
        except CircuitBreakerOpenException:
          # Handle the case where the circuit is open
          print(f"Call : Circuit is open. Skipping call.Modificato")
        except Exception as e:
        # Handle other exceptions (e.g., service failures)
          print(f"Call : Exception occurred - {e}")
        time.sleep(1)  # Wait for a second before the next call
