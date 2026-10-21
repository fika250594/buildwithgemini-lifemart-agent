import asyncio
import os
import subprocess
import time
from playwright.async_api import async_playwright

VIDEO_DIR = "/config/Desktop/BuildWithGemini"
OUTPUT_FILE = os.path.join(VIDEO_DIR, "lifemart_demo.mp4")

async def record():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
        )
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            record_video_dir="/tmp/playwright_videos",
            record_video_size={"width": 1280, "height": 800}
        )
        page = await context.new_page()

        print("Navigating to LifeMart Frontend on Cloud Run...")
        await page.goto("https://lifemart-frontend-365041171409.us-east1.run.app", wait_until="networkidle")
        await asyncio.sleep(2)

        # 1. First interaction: Show what the app does best - Browse Catalog & Inventory
        print("Clicking 'Browse Catalog' example prompt chip...")
        catalog_btn = page.locator(".prompt-chip >> text=Browse Catalog")
        await catalog_btn.click()
        
        # Wait for agent response
        print("Waiting for catalog response and A2UI cards...")
        await page.wait_for_selector(".dialogue-turn.agent:has(.bubble:not(:text('…')))", timeout=60000)
        await asyncio.sleep(4)

        # 2. Second richer prompt: Allergy safety check, cart calculation, and image generation
        print("Typing richer prompt with allergy check, cart calculation & image generation...")
        prompt_input = page.locator("#input")
        send_btn = page.locator("button[type='submit']")

        rich_prompt = "I have a strict dairy allergy. Recommend safe organic oat milk from inventory, calculate the cart total for 2 units with promo code SAVE10, and generate a photorealistic studio image of the item."
        await prompt_input.fill(rich_prompt)
        await asyncio.sleep(1)
        await send_btn.click()

        print("Waiting for rich response (A2UI card, Firestore discount breakdown & image)...")
        # Wait until a second agent response finishes loading (no longer '…')
        await page.wait_for_function(
            "document.querySelectorAll('.dialogue-turn.agent').length >= 2 && !document.querySelectorAll('.dialogue-turn.agent')[1].textContent.includes('…')",
            timeout=90000
        )
        await asyncio.sleep(6)

        # Scroll to view entire conversation
        await page.evaluate("document.getElementById('log').scrollTop = document.getElementById('log').scrollHeight")
        await asyncio.sleep(3)

        print("Closing context to finalize video...")
        await context.close()
        video_path = await page.video.path()
        await browser.close()

        print(f"Playwright video saved at: {video_path}")
        # Convert/move to destination mp4
        os.system(f"ffmpeg -y -i {video_path} -c:v libx264 -pix_fmt yuv420p {OUTPUT_FILE}")
        print(f"Final demo video created at: {OUTPUT_FILE}")

if __name__ == "__main__":
    asyncio.run(record())
