from concurrent import futures
import grpc
import mysql.connector
import yfinance as yf
from user_management_pb2 import *
from user_management_pb2_grpc import UserManagementServicer, add_UserManagementServicer_to_server
from threading import Lock


DB_CONFIG = {
    'host': 'mysql',
    'user': 'Admin',
    'password': '1234',
    'database': 'user_management'
}

request_cache={}

cache_lock=Lock()

class UserService(UserManagementServicer):
    def __init__(self):
        self.conn = mysql.connector.connect(**DB_CONFIG)
        self.cursor = self.conn.cursor()
        self.cursor.execute("SELECT email,ticker FROM users")
        users=self.cursor.fetchall()
        with cache_lock:
             for email,ticker in users:
                request_cache[email]=ticker
        print(request_cache)

    def UserCache(self, request, context):
        email, ticker = request.email, request.ticker
        meta=dict(email=email,ticker=ticker)
        print(meta)
        userid=meta.get('email','unknown')
        tickern=meta.get('ticker','unknown')

        print(f"Message received - Userid:{userid},ticker:{tickern}")

        with cache_lock:
           print("Cache context:\n")
           for entry in  request_cache:
               print(entry)
           if userid in request_cache:
               print(f"Return for request {userid} exist in cache")
               return request_cache[email],True
        with cache_lock:
           request_cache[email]=ticker
        return request_cache[email],False

    def RegisterUser(self, request, context):
        email, ticker = request.email, request.ticker
        value, stato=self.UserCache(request, context)
        print(value,stato)
        if (stato==False):
           try:
               stock = yf.Ticker(ticker)
               info=stock.info
               if 'shortName' not in info:
#                raise ValueError(f"Nessun dato valido trovato per il simbolo: {symbol}")
                   return UserResponse(success=False, message="ticker does'n exists.")
               self.cursor.execute("INSERT INTO users (email, ticker) VALUES (%s, %s)", (email, ticker))
               self.conn.commit()
               return UserResponse(success=True, message="User registered successfully.")
           except mysql.connector.IntegrityError:
               return UserResponse(success=False, message="User already exists.")

    def UpdateUser(self, request, context):
        email, new_ticker = request.email, request.new_ticker
        value, stato=self.UserCache(request, context)
        print(value,stato)
        if (stato==True):
	        with cache_lock:
           	   request_cache[email]=ticker
                
        	self.cursor.execute("UPDATE users SET ticker = %s WHERE email = %s", (new_ticker, email))
        	self.conn.commit()
        	return UserResponse(success=True, message="User updated successfully.")
        return UserResponse(success=False, message="User not {email} updated, not in queue.")


    def DeleteUser(self, request, context):
        email = request.email
        self.cursor.execute("DELETE FROM users WHERE email = %s", (email,))
        self.conn.commit()
        return DeleteResponse(success=True, message="User deleted successfully.")

    def GetLatestStockValue(self, request, context):
        email = request.email
        self.cursor.execute("SELECT ticker FROM users WHERE email = %s", (email,))
        result = self.cursor.fetchone()
        if result:
            ticker = result[0]
            stock = yf.Ticker(ticker)
            price = stock.history(period="1d")['Close'].iloc[-1]
            return StockValueResponse(ticker=ticker, value=price, timestamp=str(stock.history(period="1d").index[-1]))
        return StockValueResponse()

    def GetAverageStockValue(self, request, context):
        email, count = request.email, request.count
        self.cursor.execute("SELECT value FROM stock_data WHERE email = %s ORDER BY timestamp DESC LIMIT %s", (email, count))
        values = [row[0] for row in self.cursor.fetchall()]
        if values:
            return AverageValueResponse(average=sum(values) / len(values))
        return AverageValueResponse(average=0.0)

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    add_UserManagementServicer_to_server(UserService(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    server.wait_for_termination()

if __name__ == "__main__":
    print("Server is started")
    serve()

