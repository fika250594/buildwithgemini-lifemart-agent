#!/usr/bin/env python3
"""Seed initial products for LifeMart Marketplace into Firestore."""

from google.cloud import firestore

PROJECT_ID = "qwiklabs-gcp-03-8366b68c5e00"
COLLECTION_NAME = "products"

SAMPLE_PRODUCTS = [
    {
        "id": "prod_oat_milk",
        "name": "Organic Oat Milk (Barista Blend)",
        "category": "groceries",
        "price": 4.99,
        "unit": "32 oz",
        "stock": 45,
        "description": "Creamy, dairy-free organic oat milk perfect for coffee, smoothies, and cereal.",
        "tags": ["organic", "dairy-free", "vegan", "breakfast"],
        "rating": 4.8,
    },
    {
        "id": "prod_coffee_beans",
        "name": "Single-Origin Ethiopian Coffee Beans",
        "category": "groceries",
        "price": 14.50,
        "unit": "12 oz bag",
        "stock": 28,
        "description": "Medium roast whole bean coffee with floral jasmine and bergamot notes.",
        "tags": ["organic", "fair-trade", "coffee", "beverages"],
        "rating": 4.9,
    },
    {
        "id": "prod_olive_oil",
        "name": "Extra Virgin Olive Oil (Cold Pressed)",
        "category": "pantry",
        "price": 18.25,
        "unit": "750 ml",
        "stock": 30,
        "description": "First cold-pressed extra virgin olive oil from single-estate Mediterranean olives.",
        "tags": ["pantry-essential", "organic", "cooking", "keto"],
        "rating": 4.7,
    },
    {
        "id": "prod_laundry_sheets",
        "name": "Eco-Friendly Laundry Detergent Sheets",
        "category": "household",
        "price": 12.99,
        "unit": "60 sheets",
        "stock": 50,
        "description": "Zero-waste, plastic-free biodegradable laundry detergent sheets with fresh linen scent.",
        "tags": ["eco-friendly", "zero-waste", "cleaning", "hypoallergenic"],
        "rating": 4.8,
    },
    {
        "id": "prod_dish_soap",
        "name": "Plant-Based Citrus Dish Soap Refill",
        "category": "household",
        "price": 8.49,
        "unit": "32 oz",
        "stock": 35,
        "description": "Tough on grease, gentle on hands plant-derived dish soap with organic lemon essential oil.",
        "tags": ["eco-friendly", "cleaning", "refill", "non-toxic"],
        "rating": 4.6,
    },
    {
        "id": "prod_granola",
        "name": "Honey Almond Crunch Artisan Granola",
        "category": "groceries",
        "price": 7.20,
        "unit": "14 oz",
        "stock": 40,
        "description": "Slow-baked rolled oats with wildflower honey, roasted almonds, and pumpkin seeds.",
        "tags": ["breakfast", "gluten-free", "snacks"],
        "rating": 4.9,
    },
    {
        "id": "prod_bamboo_tp",
        "name": "100% Bamboo Premium Toilet Paper",
        "category": "household",
        "price": 22.00,
        "unit": "12 rolls (3-ply)",
        "stock": 25,
        "description": "Ultra-soft and sustainably harvested 3-ply tree-free bamboo toilet tissue.",
        "tags": ["eco-friendly", "household-essential", "sustainable"],
        "rating": 4.7,
    },
]


def seed_database():
    print(f"Connecting to Firestore with hardcoded Project ID: {PROJECT_ID}")
    db = firestore.Client(project=PROJECT_ID)
    batch = db.batch()

    for item in SAMPLE_PRODUCTS:
        doc_ref = db.collection(COLLECTION_NAME).document(item["id"])
        batch.set(doc_ref, item)

    batch.commit()
    print(f"Successfully seeded {len(SAMPLE_PRODUCTS)} products into collection '{COLLECTION_NAME}'.")


if __name__ == "__main__":
    seed_database()
