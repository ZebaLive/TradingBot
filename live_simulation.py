import cbpro
import pandas as pd
import time
# from dotenv import load_dotenv
# import os
import talib

# load_dotenv()

# Load environment variables from the .env file
public = True  # Set to False to trade with your account
dev = True  # Set to False to trade with real money

# Settings:
product_id = 'BTC-USD'  # Trading pair

starting_balance = 1000.0
rsi_period = 14
short_entry_rsi_threshold = 70
long_entry_rsi_threshold = 30
exit_rsi_threshold = 50
historical_data_limit = 200

# Coinbase Pro fee structure
maker_fee_rate = 0.005  # 0.5%
taker_fee_rate = 0.005  # 0.5%

# if dev:
#     api_key = os.getenv('DEV_API_KEY')
#     api_secret = os.getenv('DEV_API_SECRET')
#     api_passphrase = os.getenv('DEV_API_PASSPHRASE')
#     api_url = "https://api-public.sandbox.exchange.coinbase.com"
# else:
#     api_key = os.getenv('API_KEY')
#     api_secret = os.getenv('API_SECRET')
#     api_passphrase = os.getenv('API_PASSPHRASE')
#     api_url = "https://api.pro.coinbase.com"


# if public:
#     client = cbpro.PublicClient()
# else:
#     client = cbpro.AuthenticatedClient(
#         api_key, api_secret, api_passphrase, api_url)


position = None  # 'long', 'short', or None (no position)
entry_price = 0.0
balance = starting_balance

# Initialize empty DataFrame for storing live market data
columns = ['time', 'low', 'high', 'open', 'close', 'volume', 'RSI']
df_live = pd.DataFrame(columns=columns)

# Retrieve historical data
client = cbpro.PublicClient()
historical_data = client.get_product_historic_rates(product_id, granularity=60)
df_historical = pd.DataFrame(historical_data, columns=['time', 'low', 'high', 'open', 'close', 'volume'])
df_historical['time'] = pd.to_datetime(df_historical['time'], unit='s')
df_historical = df_historical.iloc[-historical_data_limit:]  # Limit historical data to desired length

# Combine historical and live data
df_combined = pd.concat([df_historical, df_live], axis=0, ignore_index=True, sort=True)

def calculate_rsi(df):
    close_prices = df['close'].values
    rsi = talib.RSI(close_prices, timeperiod=rsi_period)
    return rsi[-1]

def calculate_fee(amount, fee_rate):
    return amount * fee_rate

class Bot(cbpro.WebsocketClient):
    def on_open(self):
        global balance
        
        print("Bot is Trading!")
        print('Starting Account Balance:', balance)  
        print('-' * 100)
    def on_message(self, msg):
        global position, entry_price, balance, df_live, df_combined

        if msg['type'] != 'ticker':
            return
        
        # Get the latest ticker data from the WebSocket feed
        ticker = msg['price']
        last_trade_price = float(ticker)

        df_live.loc[pd.to_datetime(msg['time'])] = [msg['time'],
                                                float(msg['low_24h']),
                                                float(msg['high_24h']),
                                                float(msg['open_24h']),
                                                last_trade_price,
                                                float(msg['volume_24h']),
                                                0.0]
        
        # Calculate RSI
        df_combined = pd.concat([df_historical, df_live], axis=0, ignore_index=True, sort=True)
        rsi = calculate_rsi(df_combined)

        # Check for entry conditions
        if position is None:
            if rsi > short_entry_rsi_threshold:
                # Enter short position
                position = 'short'
                entry_price = last_trade_price
                print('Enter short position at $', entry_price)
            elif rsi < long_entry_rsi_threshold:
                # Enter long position
                position = 'long'
                entry_price = last_trade_price
                print('Enter long position at $', entry_price)

        # Check for exit conditions
        elif position == 'short':
            if rsi < exit_rsi_threshold:
                # Exit short position
                position = None
                exit_price = last_trade_price
                profit = (entry_price - exit_price) / entry_price
                fee = calculate_fee((entry_price + exit_price) / 2, taker_fee_rate)
                balance += balance * profit - fee
                print('Exit short position at $', exit_price)
                print('Profit:', profit)
                print('Fee:', fee)
                print('-' * 100)
                

        elif position == 'long':
            if rsi > exit_rsi_threshold:
                # Exit long position
                position = None
                exit_price = last_trade_price
                profit = (exit_price - entry_price) / entry_price
                fee = calculate_fee((entry_price + exit_price) / 2, taker_fee_rate)
                balance += balance * profit - fee
                print('Exit long position at $', exit_price)
                print('Profit:', profit)
                print('Fee:', fee)
                print('-' * 100)

    def on_close(self):
        global balance
        
        print('Final Account Balance:', round(balance, 2))
        print('-' * 30 + "-- Goodbye! --" + '-' * 30)
        
bot = Bot(products=[product_id], channels=['ticker'])
bot.start()

while True:
    try:
        time.sleep(1)  # Wait for messages

    except KeyboardInterrupt:
        print('Bot stopped by the user.')
        
        bot.close()
        break
    except Exception as e:
        print('An error occurred:', str(e))
        time.sleep(1)  # Wait for the next iteration after an error occurred