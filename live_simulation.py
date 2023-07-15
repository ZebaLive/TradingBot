from dotenv import load_dotenv
import os
import coinbasepro as cbpro
import pandas as pd
import mplfinance as mpf
import time

# Load environment variables from the .env file
load_dotenv()

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

# Initialize position variables and account balance
position = None  # 'long', 'short', or None (no position)
entry_price = 0.0
balance = starting_balance

# Initialize empty DataFrame for storing live market data
columns = ['time', 'low', 'high', 'open',
           'close', 'volume', 'SMA_short', 'SMA_long']
df_live = pd.DataFrame(columns=columns)

# Main trading loop
while True:
    try:
        # Fetch live market data
        ticker = client.get_product_ticker(product_id=product_id)
        trade = client.get_product_trades(product_id=product_id, limit=1)
        last_trade_price = float(trade[0]['price'])
        df_live.loc[pd.to_datetime(ticker['time'])] = [ticker['time'],
                                                       float(ticker['low']),
                                                       float(ticker['high']),
                                                       float(ticker['open']),
                                                       last_trade_price,
                                                       float(ticker['volume']),
                                                       0.0,
                                                       0.0]

        # Calculate moving averages
        df_live['SMA_short'] = df_live['close'].rolling(short_window).mean()
        df_live['SMA_long'] = df_live['close'].rolling(long_window).mean()

        # Get the latest row of live data
        latest_row = df_live.iloc[-1]

        # Check for entry conditions
        if position is None:
            if latest_row['SMA_short'] > latest_row['SMA_long']:
                # Enter long position
                position = 'long'
                entry_price = last_trade_price
                print('Enter long position at $', entry_price)
            elif latest_row['SMA_short'] < latest_row['SMA_long']:
                # Enter short position
                position = 'short'
                entry_price = last_trade_price
                print('Enter short position at $', entry_price)

        # Check for exit conditions
        elif position == 'long':
            if latest_row['close'] < latest_row['SMA_short']:
                # Exit long position
                position = None
                exit_price = last_trade_price
                profit = (exit_price - entry_price) / entry_price
                balance += balance * profit
                print('Exit long position at $', exit_price)
                print('Profit:', profit)

        elif position == 'short':
            if latest_row['close'] > latest_row['SMA_short']:
                # Exit short position
                position = None
                exit_price = last_trade_price
                profit = (entry_price - exit_price) / entry_price
                balance += balance * profit
                print('Exit short position at $', exit_price)
                print('Profit:', profit)

        # Print current account balance
        print('Account Balance:', balance)

        # # Plot the candlestick chart with SMA overlay
        # mpf.plot(df_live, type='candle', mav=(short_window, long_window),
        #          volume=True, title=f'{product_id} Candlestick Chart with SMA').invert_xaxis()

        # Wait for the next iteration
        # Adjust the sleep duration based on your desired frequency
        time.sleep(1)

    except KeyboardInterrupt:
        print('Bot stopped by the user.')
        break
    except Exception as e:
        print('An error occurred:', str(e))
        time.sleep(1)  # Wait for the next iteration after an error occurred
