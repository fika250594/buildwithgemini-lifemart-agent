# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
from zoneinfo import ZoneInfo

from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.cloud import firestore
from google.genai import types


MODEL = "gemini-3.8-flash"
PROJECT_ID = "qwiklabs-gcp-03-8366b68c5e00"
COLLECTION_NAME = "products"


def _get_firestore_client():
    return firestore.Client(project=PROJECT_ID)


def list_products(category: str = "") -> list[dict]:
    """Lists available marketplace products, optionally filtered by category.

    Args:
        category: Optional category filter (e.g. 'groceries', 'household', 'pantry').

    Returns:
        A list of product dictionaries containing details like name, price, stock, and unit.
    """
    db = _get_firestore_client()
    docs = db.collection(COLLECTION_NAME).stream()
    products = [doc.to_dict() for doc in docs]

    if category:
        cat_lower = category.lower().strip()
        products = [p for p in products if p.get("category", "").lower() == cat_lower]

    return products


def search_products(keyword: str) -> list[dict]:
    """Searches marketplace products by name, tag, or description keyword.

    Args:
        keyword: The search term or item name to look for (e.g. 'milk', 'coffee', 'eco').

    Returns:
        A list of matching product dictionaries.
    """
    db = _get_firestore_client()
    docs = db.collection(COLLECTION_NAME).stream()
    kw = keyword.lower().strip()
    results = []

    for doc in docs:
        p = doc.to_dict()
        name = p.get("name", "").lower()
        desc = p.get("description", "").lower()
        tags = [t.lower() for t in p.get("tags", [])]
        if kw in name or kw in desc or any(kw in t for t in tags):
            results.append(p)

    return results


def add_product(
    product_id: str,
    name: str,
    category: str,
    price: float,
    unit: str,
    stock: int,
    description: str,
    tags: list[str] = None,
) -> dict:
    """Adds a new product or updates an existing item in the marketplace inventory.

    Args:
        product_id: Unique identifier for the product (e.g. 'prod_matcha_tea').
        name: Name of the product.
        category: Category (e.g. 'groceries', 'household', 'pantry').
        price: Price in USD.
        unit: Unit or package description (e.g. '100g tin', '32 oz').
        stock: Available quantity in stock.
        description: Detailed product description.
        tags: Optional list of relevant tags (e.g. ['organic', 'tea']).

    Returns:
        A status dictionary confirming the product addition.
    """
    db = _get_firestore_client()
    doc_ref = db.collection(COLLECTION_NAME).document(product_id)
    product_data = {
        "id": product_id,
        "name": name,
        "category": category,
        "price": price,
        "unit": unit,
        "stock": stock,
        "description": description,
        "tags": tags or [],
        "rating": 5.0,
    }
    doc_ref.set(product_data)
    return {"status": "success", "message": f"Product '{name}' added successfully.", "product": product_data}


def update_product_stock(product_id: str, quantity_change: int) -> dict:
    """Updates the inventory stock level of a product (e.g., after an order or replenishment).

    Args:
        product_id: The ID of the product to update.
        quantity_change: Integer to adjust stock by (negative to decrease, positive to increase).

    Returns:
        A dictionary with the updated stock count.
    """
    db = _get_firestore_client()
    doc_ref = db.collection(COLLECTION_NAME).document(product_id)
    doc = doc_ref.get()
    if not doc.exists:
        return {"status": "error", "message": f"Product ID '{product_id}' not found."}

    current_stock = doc.to_dict().get("stock", 0)
    new_stock = max(0, current_stock + quantity_change)
    doc_ref.update({"stock": new_stock})
    return {"status": "success", "product_id": product_id, "previous_stock": current_stock, "new_stock": new_stock}


def calculate_cart_and_discounts(items: list[dict], promo_code: str = "") -> dict:
    """Calculates subtotal, bundle discounts, tax, and total for a list of shopping cart items.

    Args:
        items: List of item dicts, each with 'product_id' (str) and 'quantity' (int).
               Example: [{'product_id': 'prod_oat_milk', 'quantity': 2}]
        promo_code: Optional promo code string (e.g. 'SAVE10', 'ECO20', 'WELCOME5').

    Returns:
        A dictionary with itemized breakdown, discounts applied, taxes, and final total.
    """
    db = _get_firestore_client()
    item_breakdown = []
    subtotal = 0.0
    categories_present = set()

    for item in items:
        pid = item.get("product_id")
        qty = int(item.get("quantity", 1))
        doc = db.collection(COLLECTION_NAME).document(pid).get()
        if doc.exists:
            p_data = doc.to_dict()
            price = float(p_data.get("price", 0.0))
            line_total = price * qty
            subtotal += line_total
            category = p_data.get("category", "")
            categories_present.add(category)
            item_breakdown.append({
                "product_id": pid,
                "name": p_data.get("name"),
                "unit_price": price,
                "quantity": qty,
                "line_total": round(line_total, 2),
                "category": category,
            })
        else:
            item_breakdown.append({
                "product_id": pid,
                "name": "Unknown Product",
                "unit_price": 0.0,
                "quantity": qty,
                "line_total": 0.0,
                "error": "Product not found",
            })

    # Bundle discount rule: 10% off when mixing groceries & household
    bundle_discount = 0.0
    bundle_applied = False
    if "groceries" in categories_present and "household" in categories_present and subtotal > 20:
        bundle_discount = subtotal * 0.10
        bundle_applied = True

    # Promo code discount
    promo_discount = 0.0
    promo_clean = promo_code.strip().upper()
    if promo_clean == "SAVE10":
        promo_discount = (subtotal - bundle_discount) * 0.10
    elif promo_clean == "ECO20":
        promo_discount = (subtotal - bundle_discount) * 0.20
    elif promo_clean == "WELCOME5":
        promo_discount = 5.00

    total_discount = min(subtotal, bundle_discount + promo_discount)
    discounted_subtotal = subtotal - total_discount
    estimated_tax = round(discounted_subtotal * 0.0825, 2)  # 8.25% standard sales tax
    shipping = 0.0 if discounted_subtotal >= 35.0 or discounted_subtotal == 0 else 4.99
    final_total = round(discounted_subtotal + estimated_tax + shipping, 2)

    return {
        "items": item_breakdown,
        "subtotal": round(subtotal, 2),
        "bundle_discount": round(bundle_discount, 2),
        "bundle_applied": bundle_applied,
        "promo_discount": round(promo_discount, 2),
        "promo_code_applied": promo_clean if promo_discount > 0 else None,
        "total_savings": round(total_discount, 2),
        "estimated_tax": estimated_tax,
        "shipping": shipping,
        "free_shipping": shipping == 0.0,
        "final_total": final_total,
    }


def checkout_order(items: list[dict], delivery_address: str, promo_code: str = "", user_notes: str = "") -> dict:
    """Processes a checkout order, decrements stock in Firestore, and records the order.

    Args:
        items: List of item dicts with 'product_id' (str) and 'quantity' (int).
        delivery_address: Shipping destination address.
        promo_code: Optional discount code.
        user_notes: Optional special instructions or notes.

    Returns:
        A dictionary with order confirmation details, order ID, and delivery estimate.
    """
    db = _get_firestore_client()
    
    # 1. Verify stock availability
    for item in items:
        pid = item.get("product_id")
        qty = int(item.get("quantity", 1))
        doc = db.collection(COLLECTION_NAME).document(pid).get()
        if not doc.exists:
            return {"status": "error", "message": f"Product '{pid}' does not exist."}
        stock = doc.to_dict().get("stock", 0)
        if stock < qty:
            pname = doc.to_dict().get("name", pid)
            return {"status": "error", "message": f"Insufficient stock for '{pname}'. Available: {stock}, requested: {qty}."}

    # 2. Compute finalized pricing
    pricing = calculate_cart_and_discounts(items, promo_code=promo_code)

    # 3. Decrement inventory
    for item in items:
        pid = item.get("product_id")
        qty = int(item.get("quantity", 1))
        doc_ref = db.collection(COLLECTION_NAME).document(pid)
        current_stock = doc_ref.get().to_dict().get("stock", 0)
        doc_ref.update({"stock": max(0, current_stock - qty)})

    # 4. Save order record
    order_id = f"ord_{int(datetime.datetime.now().timestamp())}"
    estimated_delivery = (datetime.datetime.now() + datetime.timedelta(days=2)).strftime("%A, %B %d, %Y")
    order_doc = {
        "order_id": order_id,
        "items": pricing["items"],
        "pricing": {
            "subtotal": pricing["subtotal"],
            "total_savings": pricing["total_savings"],
            "tax": pricing["estimated_tax"],
            "shipping": pricing["shipping"],
            "final_total": pricing["final_total"],
        },
        "delivery_address": delivery_address,
        "delivery_estimate": estimated_delivery,
        "user_notes": user_notes,
        "status": "CONFIRMED",
        "created_at": datetime.datetime.now().isoformat(),
    }
    db.collection("orders").document(order_id).set(order_doc)

    return {
        "status": "success",
        "order_id": order_id,
        "estimated_delivery": estimated_delivery,
        "final_total": pricing["final_total"],
        "message": f"Order {order_id} successfully confirmed! Delivery scheduled for {estimated_delivery}.",
        "order_summary": order_doc,
    }


def estimate_pantry_replenishment(purchased_items: list[dict], household_size: int = 2) -> dict:
    """Estimates how long purchased household/grocery goods will last and predicts replenishment dates.

    Args:
        purchased_items: List of item dicts with 'product_id' and optional 'quantity'.
        household_size: Number of people in the household (default: 2).

    Returns:
        A dictionary with estimated days remaining and recommended next reorder dates.
    """
    db = _get_firestore_client()
    schedule = []
    
    # Standard daily consumption rates per person for sample catalog items
    rates = {
        "prod_oat_milk": {"daily_person": 4.0, "unit": "oz"},       # 32 oz / (4 oz/day * size)
        "prod_coffee_beans": {"daily_person": 0.5, "unit": "oz"},   # 12 oz / (0.5 oz/day * size)
        "prod_olive_oil": {"daily_person": 10.0, "unit": "ml"},     # 750 ml / (10 ml/day * size)
        "prod_laundry_sheets": {"daily_person": 0.35, "unit": "loads"}, # 60 loads
        "prod_dish_soap": {"daily_person": 0.3, "unit": "oz"},      # 32 oz
        "prod_granola": {"daily_person": 1.5, "unit": "oz"},        # 14 oz
        "prod_bamboo_tp": {"daily_person": 0.15, "unit": "rolls"},  # 12 rolls
    }

    now = datetime.datetime.now()

    for item in purchased_items:
        pid = item.get("product_id")
        qty = int(item.get("quantity", 1))
        doc = db.collection(COLLECTION_NAME).document(pid).get()
        pname = doc.to_dict().get("name", pid) if doc.exists else pid

        if pid in rates:
            daily_use = rates[pid]["daily_person"] * max(1, household_size)
            if pid == "prod_oat_milk":
                capacity = 32.0 * qty
            elif pid == "prod_coffee_beans":
                capacity = 12.0 * qty
            elif pid == "prod_olive_oil":
                capacity = 750.0 * qty
            elif pid == "prod_laundry_sheets":
                capacity = 60.0 * qty
            elif pid == "prod_dish_soap":
                capacity = 32.0 * qty
            elif pid == "prod_granola":
                capacity = 14.0 * qty
            elif pid == "prod_bamboo_tp":
                capacity = 12.0 * qty
            else:
                capacity = 30.0 * qty

            days_lasting = max(1, int(capacity / daily_use))
        else:
            days_lasting = 14 * qty  # fallback estimate: 2 weeks per unit

        reorder_date = (now + datetime.timedelta(days=max(1, days_lasting - 3))).strftime("%Y-%m-%d")
        depletion_date = (now + datetime.timedelta(days=days_lasting)).strftime("%Y-%m-%d")

        schedule.append({
            "product_id": pid,
            "product_name": pname,
            "quantity": qty,
            "estimated_days_supply": days_lasting,
            "estimated_depletion_date": depletion_date,
            "recommended_reorder_date": reorder_date,
        })

    return {
        "household_size": household_size,
        "replenishment_schedule": schedule,
        "recommendation": "Set reorder reminders 3 days prior to estimated depletion.",
    }


import urllib.request
import json
import urllib.parse


def fetch_global_market_products(query: str = "", category: str = "groceries") -> list[dict]:
    """Fetches real-time external products and price benchmarks from a free public marketplace catalog API.

    Args:
        query: Optional search keyword (e.g. 'milk', 'coffee', 'soap', 'rice').
        category: Product category (e.g. 'groceries', 'beauty', 'fragrances').

    Returns:
        A list of standardized external products with title, price, category, rating, and thumbnail.
    """
    try:
        if query:
            url = f"https://dummyjson.com/products/search?q={urllib.parse.quote(query)}"
        elif category:
            url = f"https://dummyjson.com/products/category/{urllib.parse.quote(category)}"
        else:
            url = "https://dummyjson.com/products?limit=10"

        req = urllib.request.Request(url, headers={"User-Agent": "LifeMartAgent/1.0"})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
            raw_products = data.get("products", [])

        results = []
        for p in raw_products[:6]:  # Keep response concise
            results.append({
                "external_id": f"ext_{p.get('id')}",
                "title": p.get("title"),
                "category": p.get("category"),
                "price": p.get("price"),
                "rating": p.get("rating"),
                "stock": p.get("stock"),
                "brand": p.get("brand", "Generic"),
                "description": p.get("description"),
                "thumbnail": p.get("thumbnail"),
            })
        return results
    except Exception as e:
        return [{"error": f"Failed to fetch external market data: {str(e)}"}]


import os
import math


def geocode_address(address: str) -> dict:
    """Geocodes a street address into geographic coordinates (latitude and longitude).

    Args:
        address: The address string (e.g. '1600 Amphitheatre Pkwy, Mountain View, CA').

    Returns:
        A dictionary containing the formatted address and location coordinates {lat, lng}.
    """
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY", "").strip()
    if not api_key or api_key == "PASTE_KEY_HERE":
        return {"error": "GOOGLE_MAPS_API_KEY is not configured in .env."}

    try:
        url = f"https://maps.googleapis.com/maps/api/geocode/json?address={urllib.parse.quote(address)}&key={api_key}"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))

        if data.get("status") != "OK" or not data.get("results"):
            return {"error": f"Geocoding failed: {data.get('status', 'Unknown error')}"}

        res = data["results"][0]
        return {
            "formatted_address": res.get("formatted_address"),
            "location": res.get("geometry", {}).get("location", {}),
            "place_id": res.get("place_id"),
        }
    except Exception as e:
        return {"error": f"Geocoding request failed: {str(e)}"}


def find_nearby_places(latitude: float, longitude: float, place_type: str = "supermarket", radius_meters: float = 3000.0) -> list[dict]:
    """Finds nearby places (e.g. supermarkets, convenience stores, pharmacies) using Places API (New).

    Args:
        latitude: Center latitude coordinate.
        longitude: Center longitude coordinate.
        place_type: Type of place to search for (e.g. 'supermarket', 'grocery_store', 'pharmacy', 'convenience_store').
        radius_meters: Search radius in meters (default: 3000m / 3km).

    Returns:
        A list of nearby places with name, formatted address, and location coordinates.
    """
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY", "").strip()
    if not api_key or api_key == "PASTE_KEY_HERE":
        return [{"error": "GOOGLE_MAPS_API_KEY is not configured in .env."}]

    try:
        url = "https://places.googleapis.com/v1/places:searchNearby"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location,places.types",
        }
        body = {
            "includedTypes": [place_type],
            "maxResultCount": 5,
            "locationRestriction": {
                "circle": {
                    "center": {
                        "latitude": latitude,
                        "longitude": longitude,
                    },
                    "radius": radius_meters,
                }
            },
        }

        req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))

        places = []
        for p in data.get("places", []):
            name_obj = p.get("displayName", {})
            name = name_obj.get("text", "") if isinstance(name_obj, dict) else str(name_obj)
            places.append({
                "name": name,
                "address": p.get("formattedAddress"),
                "location": p.get("location"),
                "types": p.get("types", []),
            })
        return places
    except Exception as e:
        return [{"error": f"Places search failed: {str(e)}"}]


def calculate_shipping_fee_by_distance(destination_address: str, store_lat: float = 40.7128, store_lng: float = -74.0060) -> dict:
    """Calculates delivery shipping fee based on real geocoded distance from the distribution hub.

    Args:
        destination_address: Customer's delivery destination address.
        store_lat: Origin warehouse/hub latitude (default: Manhattan NY Hub 40.7128).
        store_lng: Origin warehouse/hub longitude (default: Manhattan NY Hub -74.0060).

    Returns:
        A dictionary with distance in km, delivery zone tier, and calculated shipping fee.
    """
    geo_res = geocode_address(destination_address)
    if "error" in geo_res:
        return {"error": geo_res["error"], "fallback_shipping_fee": 4.99}

    loc = geo_res.get("location", {})
    dest_lat = loc.get("lat")
    dest_lng = loc.get("lng")
    if dest_lat is None or dest_lng is None:
        return {"error": "Could not determine destination coordinates.", "fallback_shipping_fee": 4.99}

    # Haversine distance formula (in km)
    R = 6371.0
    dlat = math.radians(dest_lat - store_lat)
    dlng = math.radians(dest_lng - store_lng)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(store_lat)) * math.cos(math.radians(dest_lat)) * math.sin(dlng / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance_km = round(R * c, 2)

    # Shipping pricing tier:
    # < 5 km: $2.99 local dispatch
    # 5-20 km: $4.99 regional metro
    # > 20 km: $4.99 + $0.50 per additional 5 km
    if distance_km < 5.0:
        fee = 2.99
        tier = "Hyper-Local Express"
    elif distance_km <= 20.0:
        fee = 4.99
        tier = "Regional Metro"
    else:
        extra_dist = distance_km - 20.0
        fee = round(4.99 + (extra_dist / 5.0) * 0.50, 2)
        tier = "Extended Delivery"

    return {
        "destination_address": geo_res.get("formatted_address"),
        "coordinates": {"lat": dest_lat, "lng": dest_lng},
        "distance_km": distance_km,
        "delivery_tier": tier,
        "shipping_fee": fee,
    }


from google import genai
from google.cloud import storage
from google.adk.tools import ToolContext


BUCKET_NAME = "lifemart-assets-qwiklabs-gcp-03-8366b68c5e00"


async def generate_product_image(prompt: str, item_name: str, tool_context: ToolContext = None) -> dict:
    """Generates an image for a product or bundle using gemini-3.1-flash-lite-image in the global region.
    Saves the image as an artifact for the Playground and uploads it to the public Cloud Storage bucket.

    Args:
        prompt: Description of the product image to generate (e.g. 'A fresh glass bottle of organic oat milk with oats and green leaves on a modern wooden kitchen counter, photorealistic studio lighting').
        item_name: Short identifier/name for the item (e.g. 'oat_milk_bottle').
        tool_context: Tool context injected by ADK for artifact saving.

    Returns:
        A dictionary with the public image URL, filename, and confirmation status.
    """
    try:
        # Initialize GenAI client pointing to global Vertex AI
        client = genai.Client(
            vertexai=True,
            project=PROJECT_ID,
            location="global",
        )

        # Call gemini-3.1-flash-lite-image with response modalities
        response = await client.aio.models.generate_content(
            model="gemini-3.1-flash-lite-image",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=[types.Modality.TEXT, types.Modality.IMAGE],
            ),
        )

        image_bytes = None
        for candidate in response.candidates:
            if candidate.content and candidate.content.parts:
                for part in candidate.content.parts:
                    if part.inline_data and part.inline_data.data:
                        image_bytes = part.inline_data.data
                        break
            if image_bytes:
                break

        if not image_bytes:
            return {"error": "Model did not return image data."}

        clean_name = "".join(c if c.isalnum() or c in "_-" else "_" for c in item_name.lower())
        timestamp = int(datetime.datetime.now().timestamp())
        filename = f"{clean_name}_{timestamp}.png"

        # 1. Save artifact to ADK ToolContext so it renders in Playground
        if tool_context:
            artifact_part = types.Part.from_bytes(data=image_bytes, mime_type="image/png")
            await tool_context.save_artifact(filename=filename, artifact=artifact_part)

        # 2. Upload directly to public GCS bucket
        storage_client = storage.Client(project=PROJECT_ID)
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(filename)
        blob.upload_from_string(image_bytes, content_type="image/png")

        public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{filename}"

        return {
            "status": "success",
            "item_name": item_name,
            "filename": filename,
            "public_url": public_url,
            "message": f"Generated image for '{item_name}' and published to {public_url}",
        }

    except Exception as e:
        return {"error": f"Image generation or upload failed: {str(e)}"}


from google.adk.code_executors.agent_engine_sandbox_code_executor import AgentEngineSandboxCodeExecutor

from google.adk.agents.callback_context import CallbackContext
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.adk.memory import VertexAiMemoryBankService

MEMORY_BANK_ID = "3156437299089113088"
LOCATION = "us-east1"


async def generate_memories_callback(callback_context: CallbackContext):
    """Saves session conversations to Vertex AI Memory Bank for cross-session facts/preferences extraction."""
    await callback_context.add_session_to_memory()
    return None


def memory_bank_service_builder():
    """Builds the Vertex AI Memory Bank service using our deployed Agent Engine instance."""
    return VertexAiMemoryBankService(
        project=PROJECT_ID,
        location=LOCATION,
        agent_engine_id=MEMORY_BANK_ID,
    )


root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model=MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=(
        "You are LifeMart Concierge, an intelligent everyday living and marketplace assistant.\n\n"
        "MEMORY & SAFETY RULES:\n"
        "- Long-term memory is active. You MUST proactively capture and remember all user-stated allergies "
        "(e.g., dairy, peanuts, gluten, soy, shellfish, bee venom, latex, etc.), medical dietary restrictions, "
        "and household sensitivities across conversations.\n"
        "- Whenever a user reveals an allergy, acknowledge it and commit it to memory so future sessions recall it.\n"
        "- When recommending products, building grocery carts, or suggesting alternatives, ALWAYS cross-check the user's "
        "known allergies retrieved from memory and strictly filter out or warn about any conflicting ingredients or allergens.\n\n"
        "CORE CAPABILITIES:\n"
        "You help users discover products, check stock, browse categories, manage inventory, "
        "calculate cart prices and bundle discounts, place orders, compare global market prices, "
        "geocode delivery addresses, count distance-based shipping fees, locate nearby supply hubs, "
        "generate photorealistic product visuals, and perform complex calculations or simulations via sandboxed Python code."
    ),
    code_executor=AgentEngineSandboxCodeExecutor(
        agent_engine_resource_name=AGENT_ENGINE_RESOURCE,
    ),
    tools=[
        PreloadMemoryTool(),
        list_products,
        search_products,
        add_product,
        update_product_stock,
        calculate_cart_and_discounts,
        checkout_order,
        estimate_pantry_replenishment,
        fetch_global_market_products,
        geocode_address,
        find_nearby_places,
        calculate_shipping_fee_by_distance,
        generate_product_image,
    ],
    after_agent_callback=generate_memories_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)






