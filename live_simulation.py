import cbpro
import pandas as pd
import time
from dotenv import load_dotenv
import mplfinance as mpf
import os

load_dotenv()

# Load environment variables from the .env file
public = True  # Set to False to trade with your account
dev = True  # Set to False to trade with real money

# Settings:
product_id = 'BTC-USD'  # Trading pair
short_window = 50
long_window = 200
starting_balance = 100.0  # Starting account balance
# Candlestick data granularity in seconds (86400 sec = 1 day)
granularity = 86400

if dev:
    api_key = os.getenv('DEV_API_KEY')
    api_secret = os.getenv('DEV_API_SECRET')
    api_passphrase = os.getenv('DEV_API_PASSPHRASE')
    api_url = "https://api-public.sandbox.exchange.coinbase.com"
else:
    api_key = os.getenv('API_KEY')
    api_secret = os.getenv('API_SECRET')
    api_passphrase = os.getenv('API_PASSPHRASE')
    api_url = "https://api.pro.coinbase.com"


if public:
    client = cbpro.PublicClient()
else:
    client = cbpro.AuthenticatedClient(
        api_key, api_secret, api_passphrase, api_url)


position = None  # 'long', 'short', or None (no position)
entry_price = 0.0
balance = starting_balance

# Fetch historical data
client = cbpro.PublicClient()
historical_data = client.get_product_historic_rates(product_id, granularity=60)
df_historical = pd.DataFrame(historical_data, columns=['time', 'low', 'high', 'open', 'close', 'volume'])
df_historical['time'] = pd.to_datetime(df_historical['time'], unit='s')
df_historical.set_index('time', inplace=True)

df_live = pd.concat([df_historical, pd.DataFrame(columns=['SMA_short', 'SMA_long'])])

def calculate_indicators(df):
    # Calculate moving averages
    df['SMA_short'] = df['close'].rolling(short_window).mean()
    df['SMA_long'] = df['close'].rolling(long_window).mean()

    return df

# Calculate indicators for the combined data
df_live = calculate_indicators(df_live)

# # Initialize empty DataFrame for storing live market data
# columns = ['time', 'low', 'high', 'open', 'close', 'volume', 'SMA_short', 'SMA_long']
# df_live = pd.DataFrame(columns=columns)

class Bot(cbpro.WebsocketClient):
    def on_open(self):
        print("Bot is listening!")
    def on_message(self, msg):
        global position, entry_price, balance, df_live

        if msg['type'] != 'ticker':
            return
        
        # Get the latest ticker data from the WebSocket feed
        ticker = msg['price']
        side = msg['side']
        last_trade_price = float(ticker)

        df_live.loc[pd.to_datetime(msg['time'])] = [msg['time'],
                                                    float(msg['low_24h']),
                                                    float(msg['high_24h']),
                                                    float(msg['open_24h']),
                                                    last_trade_price,
                                                    float(msg['volume_24h']),
                                                    0.0,
                                                    0.0]

        # Calculate moving averages
        df_live['SMA_short'] = df_live['close'].rolling(short_window).mean()
        df_live['SMA_long'] = df_live['close'].rolling(long_window).mean()

        # Get the latest row of live data
        latest_row = df_live.iloc[-1]

        # Check for entry conditions
        if position is None:
            if latest_row['SMA_short'] > latest_row['SMA_long'] and side == 'buy':
                # Enter long position
                position = 'long'
                entry_price = last_trade_price
                print('Enter long position at $', entry_price)
            elif latest_row['SMA_short'] < latest_row['SMA_long'] and side == 'sell':
                # Enter short position
                position = 'short'
                entry_price = last_trade_price
                print('Enter short position at $', entry_price)

        # Check for exit conditions
        elif position == 'long' and side == 'sell':
            if latest_row['close'] < latest_row['SMA_short']:
                # Exit long position
                position = None
                exit_price = last_trade_price
                profit = (exit_price - entry_price) / entry_price
                balance += balance * profit
                print('Exit long position at $', exit_price)
                print('Profit:', profit)
                print('Account Balance:', balance)

        elif position == 'short' and side == 'buy':
            if latest_row['close'] > latest_row['SMA_short']:
                # Exit short position
                position = None
                exit_price = last_trade_price
                profit = (entry_price - exit_price) / entry_price
                balance += balance * profit
                print('Exit short position at $', exit_price)
                print('Profit:', profit)
                print('Account Balance:', balance)

        # Print current account balance
        
    def on_close(self):
        print("-- Goodbye! --")
    
print('Account Balance:', balance)   
bot = Bot(products=[product_id], channels=['ticker'])
bot.start()

while bot.ws.sock.connected:
    try:
        time.sleep(1)  # Wait for messages

    except KeyboardInterrupt:
        print('Bot stopped by the user.')
        bot.close()
        break
    except Exception as e:
        print('An error occurred:', str(e))
        time.sleep(1)  # Wait for the next iteration after an error occurred