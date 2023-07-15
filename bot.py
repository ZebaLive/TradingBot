from dotenv import load_dotenv
import os
import coinbasepro as cbpro

# Load environment variables from the .env file
load_dotenv()

# Retrieve environment variables
api_key = os.getenv('API_KEY')
api_secret = os.getenv('API_SECRET')
api_passphrase = os.getenv('API_PASSPHRASE')

client = cbpro.AuthenticatedClient(
    api_key, api_secret, api_passphrase, "https://api-public.sandbox.exchange.coinbase.com")

# Test the connection by fetching your account information
accounts = client.get_accounts()
print(accounts)
