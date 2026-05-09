import requests
import json

BASE_URL = "http://127.0.0.1:8000/api/v1"
API_KEY = "sk_test_key_1234567890"

def test_health():
    print("Testing /health...")
    response = requests.get(f"{BASE_URL}/health")
    print(response.status_code, response.json())

def test_balance():
    print("\nTesting /balance...")
    headers = {"X-API-Key": API_KEY}
    response = requests.get(f"{BASE_URL}/balance", headers=headers)
    print(response.status_code, response.json())

def test_products():
    print("\nTesting /products...")
    headers = {"X-API-Key": API_KEY}
    response = requests.get(f"{BASE_URL}/products", headers=headers)
    print(response.status_code, response.json())
    return response.json().get("products", [])

def test_buy(product_id):
    print(f"\nTesting /buy for product_id {product_id}...")
    headers = {"X-API-Key": API_KEY, "Content-Type": "application/json"}
    payload = {"product_id": product_id, "quantity": 1}
    response = requests.post(f"{BASE_URL}/buy", headers=headers, json=payload)
    print(response.status_code, response.json())

def test_cmsnt():
    print("\n--- Testing CMSNT Compatibility ---")
    headers = {"X-API-Key": API_KEY}
    
    print("Testing CMSNT /balance...")
    resp = requests.get("http://127.0.0.1:8000/api/cmsnt/v1/balance", headers=headers)
    print(resp.status_code, resp.json())
    
    print("Testing CMSNT /products...")
    resp = requests.get("http://127.0.0.1:8000/api/cmsnt/v1/products", headers=headers)
    print(resp.status_code, resp.json())
    products = resp.json().get("data", [])
    
    if products:
        p_id = products[0]['id']
        print(f"Testing CMSNT /buy for product_id {p_id}...")
        resp = requests.post("http://127.0.0.1:8000/api/cmsnt/v1/buy", headers=headers, json={"product_id": p_id, "quantity": 1})
        print(resp.status_code, resp.json())

if __name__ == "__main__":
    test_health()
    test_balance()
    products = test_products()
    if products:
        stocked_products = [p for p in products if p['stock'] > 0]
        if stocked_products:
            test_buy(stocked_products[0]['id'])
    
    # Test CMSNT
    test_cmsnt()
