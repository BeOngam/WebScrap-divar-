import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe"
        )
        context = await browser.new_context()
        page = await context.new_page()
        await page.goto('https://divar.ir/')
        input("بعد از لاگین دستی در مرورگر، اینجا Enter بزن: ")
        await context.storage_state(path="divar_auth.json")
        print("ذخیره شد.")
        await browser.close()

asyncio.run(main())