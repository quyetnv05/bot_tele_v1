import requests
import json

url = "http://localhost:8000/webhook/sepay"
headers = {
    "Authorization": "Apikey account_digital",
    "Content-Type": "application/json"
}
data = {
    "transferAmount": 53000,
    "content": "BUY1U2114484067S9934" # the code from the screenshot the user sent
}

response = requests.post(url, headers=headers, json=data)
print("Status Code:", response.status_code)
print("Response:", response.text)
