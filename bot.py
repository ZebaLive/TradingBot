from dotenv import load_dotenv
import os
import coinbasepro as cbpro
import pandas as pd
import mplfinance as mpf

# Load environment variables from the .env file
load_dotenv()

dev = True  # Set to False to trade with real money

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


client = cbpro.AuthenticatedClient(
    api_key, api_secret, api_passphrase, api_url)

# # Test the connection by fetching your account information
# accounts = client.get_accounts()
# print(accounts)

product_id = 'BTC-USD'

# Fetch market data
candles = client.get_product_historic_rates(
    product_id, granularity=3600)  # Hourly data
df = pd.DataFrame(candles, columns=[
                  'time', 'low', 'high', 'open', 'close', 'volume'])

# Convert columns to appropriate data types
df[['low', 'high', 'open', 'close', 'volume']] = df[[
    'low', 'high', 'open', 'close', 'volume']].astype(float)

# Convert timestamp to datetime and set as index
df['time'] = pd.to_datetime(df['time'], unit='s')
df.set_index('time', inplace=True)

# Calculate a simple moving average (SMA) with a window of 20 periods
sma_window = 20
df['SMA'] = df['close'].rolling(sma_window).mean()

# Plot the candlestick chart with SMA overlay
mpf.plot(df, type='candle', mav=(sma_window,), volume=True,
         title='BTC-USD Candlestick Chart with SMA')
