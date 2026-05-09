import aiohttp
import os
import logging
import time
import asyncio

class PartnerAPIClient:
    def __init__(self):
        from dotenv import load_dotenv
        load_dotenv()
        self.base_url = "http://node12.zampto.net:20291/api"
        self.api_key = os.getenv("PARTNER_API_KEY")
        self.headers = {"X-API-Key": self.api_key or ""}
        self.products_cache = None # Expose directly for speed
        self.stock_history = {} # Track partner_id -> stock level

    async def get_products(self, force=False):
        if not force and self.products_cache:
            return self.products_cache
        
        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.get(f"{self.base_url}/products", timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data and data.get("success"):
                            # Detect stock changes before updating cache
                            restocked = []
                            new_products = data.get("products", [])
                            
                            for p in new_products:
                                p_id = str(p["id"])
                                new_stock = p.get("stock", 0)
                                old_stock = self.stock_history.get(p_id, 0)
                                
                                # If stock increased and is now > 0
                                if new_stock > old_stock and new_stock > 0:
                                    restocked.append({
                                        "id": p_id,
                                        "name": p["name"],
                                        "added_count": new_stock - old_stock,
                                        "current_stock": new_stock
                                    })
                                
                                # Update history
                                self.stock_history[p_id] = new_stock
                            
                            self.products_cache = data
                            data["restocked"] = restocked # Attach to result for task handling
                        return data
                    return await response.json()
        except Exception as e:
            logging.error(f"API Error: {e}")
            return self.products_cache or {"success": False}

    async def get_balance(self):
        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.get(f"{self.base_url}/balance", timeout=10) as response:
                    return await response.json()
        except Exception: return {"success": False}

    async def get_health(self):
        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.get(f"{self.base_url}/health", timeout=10) as response:
                    return await response.json()
        except Exception: return {"success": False, "message": "API is unreachable"}

    async def buy_product(self, product_id: str, quantity: int = 1):
        payload = {"product_id": product_id, "quantity": quantity}
        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.post(f"{self.base_url}/buy", json=payload, timeout=30) as response:
                    return await response.json()
        except Exception: return {"success": False}

    async def close(self):
        # Placeholder for cleanup if needed. 
        # Currently each method uses its own session via 'async with'.
        pass

partner_api = PartnerAPIClient()
