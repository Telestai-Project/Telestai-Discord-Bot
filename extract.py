from dotenv import load_dotenv
import os
import requests

# Load environment variables from the .env file
load_dotenv()

def get_balances():
    ltc_address = 'ltc1qz9n323uxvjkkc98qsqwcnp4eu0mxv27earydhp'
    usdt_address = '0x4EBAAAcBcae2D5465ccF1f88efcf3a614b233589'
    usdt_contract_address = '0xdAC17F958D2ee523a2206206994597C13D831ec7'
    etherscan_api_key = os.getenv('ETHERSCAN_API_TOKEN')

    # Check if the API key is properly loaded
    if not etherscan_api_key:
        return {"error": "ETHERSCAN_API_TOKEN is not set in the .env file"}

    # Fetch LTC balance
    ltc_api_url = f'https://chainz.cryptoid.info/ltc/api.dws?q=getbalance&a={ltc_address}'
    # Fetch LTC to USD rate
    ltc_to_usd_url = 'https://api.coingecko.com/api/v3/simple/price?ids=litecoin&vs_currencies=usd'

    # Fetch USDT balance
    usdt_api_url = (f'https://api.etherscan.io/api'
                    f'?module=account&action=tokenbalance'
                    f'&contractaddress={usdt_contract_address}'
                    f'&address={usdt_address}'
                    f'&tag=latest&apikey={etherscan_api_key}')

    try:
        ltc_response = requests.get(ltc_api_url)
        ltc_rate_response = requests.get(ltc_to_usd_url)
        usdt_response = requests.get(usdt_api_url)

        ltc_balance = float(ltc_response.text)
        ltc_rate_data = ltc_rate_response.json()
        ltc_to_usd_rate = ltc_rate_data['litecoin']['usd']

        usdt_data = usdt_response.json()
        usdt_balance = float(usdt_data['result']) / 1e6  # Convert USDT balance from wei

        ltc_balance_in_usd = ltc_balance * ltc_to_usd_rate
        total_raised_in_usd = ltc_balance_in_usd + usdt_balance

        return {
            "ltcBalance": ltc_balance,  # LTC balance
            "usdtBalance": usdt_balance,  # USDT balance
            "ltcToUsdRate": ltc_to_usd_rate,  # LTC to USD rate
            "totalRaisedInUsd": total_raised_in_usd,  # Total raised in USD
        }
    except Exception as error:
        return {"error": "Failed to fetch balances"}

# Example usage
if __name__ == "__main__":
    balances = get_balances()
    print(balances)
