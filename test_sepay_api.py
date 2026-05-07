import requests
from dotenv import load_dotenv
import os

load_dotenv()
api_key = os.getenv("SEPAY_API_KEY")

headers = {"Authorization": f"Bearer {api_key}"}
response = requests.get("https://my.sepay.vn/userapi/transactions/list", headers=headers)
print("Status:", response.status_code)
try:
    data = response.json()
    print("Response JSON Keys:", data.keys())
    if "transactions" in data:
        print("Number of transactions:", len(data["transactions"]))
        if len(data["transactions"]) > 0:
            tx = data["transactions"][0]
            print("First transaction keys:", tx.keys())
            print("Example content:", tx.get("transaction_content", "None"))
            print("Example amount_in:", tx.get("amount_in", "None"))
except Exception as e:
    print("Error parsing JSON:", e)
