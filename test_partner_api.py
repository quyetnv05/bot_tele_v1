import asyncio
from dotenv import load_dotenv
load_dotenv()
from bot.partner_api import partner_api

async def test_api():
    print("Testing Partner API connection...")
    
    print("\n1. Testing /health...")
    health = await partner_api.get_health()
    print(health)
    
    print("\n2. Testing /balance (Requires Auth)...")
    balance = await partner_api.get_balance()
    print(balance)
    
    print("\n3. Testing /products (Requires Auth)...")
    products = await partner_api.get_products()
    if products and products.get("success"):
        prods = products.get("products", [])
        print(f"Success! Found {len(prods)} products.")
        if prods:
            print(f"First product: {prods[0].get('name')} - {prods[0].get('price')}đ - Stock: {prods[0].get('stock')}")
    else:
        print("Failed to fetch products:", products)

if __name__ == "__main__":
    asyncio.run(test_api())
