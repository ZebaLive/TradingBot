from dotenv import load_dotenv
import os
import coinbasepro as cbpro
import pandas as pd
import mplfinance as mpf

# Load environment variables from the .env file
load_dotenv()

public = True  # Set to False to trade with your account
dev = True  # Set to False to trade with real money


# Settings:
product_id = 'BTC-USD'  # Trading pair
short_window = 50
long_window = 200
starting_balance = 1000.0  # Starting account balance
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

# Fetch market data
candles = client.get_product_historic_rates(
    product_id, granularity=granularity)  # Daily data
df = pd.DataFrame(candles, columns=[
                  'time', 'low', 'high', 'open', 'close', 'volume'])

# Convert columns to appropriate data types
df[['low', 'high', 'open', 'close', 'volume']] = df[[
    'low', 'high', 'open', 'close', 'volume']].astype(float)

# Convert timestamp to datetime and set as index
df['time'] = pd.to_datetime(df['time'], unit='s')
df.set_index('time', inplace=True)

# Reverse the order of the DataFrame
df = df.iloc[::-1]

# Calculate moving averages
df['SMA_short'] = df['close'].rolling(short_window).mean()
df['SMA_long'] = df['close'].rolling(long_window).mean()

# Initialize position variables and account balance
position = None  # 'long', 'short', or None (no position)
entry_price = 0.0
balance = starting_balance

# Implement trading strategy
for index, row in df.iterrows():
    close_price = row['close']
    sma_short = row['SMA_short']
    sma_long = row['SMA_long']

    if position is None:
        # No position, check for entry conditions
        if sma_short > sma_long:
            # Enter long position
            position = 'long'
            entry_price = close_price
            print('Enter long position at $', entry_price)
        elif sma_short < sma_long:
            # Enter short position
            position = 'short'
            entry_price = close_price
            print('Enter short position at $', entry_price)

    elif position == 'long':
        # Check for exit condition for long position
        if close_price < sma_short:
            # Exit long position
            position = None
            exit_price = close_price
            profit = (exit_price - entry_price) / entry_price
            balance += balance * profit
            print('Exit long position at $', exit_price)
            print('Profit:', profit)

    elif position == 'short':
        # Check for exit condition for short position
        if close_price > sma_short:
            # Exit short position
            position = None
            exit_price = close_price
            profit = (entry_price - exit_price) / entry_price
            balance += balance * profit
            print('Exit short position at $', exit_price)
            print('Profit:', profit)

# Calculate total profit
total_profit = balance - starting_balance
print('Total Profit:', total_profit)

# Plot the candlestick chart with SMA overlay
mpf.plot(df, type='candle', mav=(short_window, long_window), volume=True,
         title=f"{product_id} Candlestick Chart with SMA")
