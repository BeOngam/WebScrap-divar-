# 🕷️ Divar Scraper

An async scraper for extracting listing information from [Divar](https://divar.ir) — title, phone number, and all images for each listing — with clean output in CSV, a text report, and organized image folders.

---

## ✨ Features

- Extracts the **title** of each listing
- Retrieves the **phone number** by automatically clicking the "Show Number" button
- Downloads up to **8 images** per listing — directly from the DOM, **without clicking the carousel**
- Saves output as a **CSV** file and a **text report**
- Organizes images into folders: `images/ad_001/image_01.jpg`
- Supports Divar **authentication sessions** (required to access phone numbers)
- Error handling: if one listing fails, the rest continue processing

---

## 📋 Prerequisites

- Python 3.10+
- Google Chrome installed on your system
- The following libraries:

```bash
pip install playwright aiohttp aiofiles
playwright install chromium
```

---

## 🚀 How to Use

### 1. Enter Your Listing Links

Open `divar_scraper.py` and add your target listing URLs to the `MY_AD_LINKS` list:

```python
MY_AD_LINKS = [
    "https://divar.ir/v/xxxxxxxx",
    "https://divar.ir/v/yyyyyyyy",
    # ...
]
```

### 2. Run the Scraper

```bash
python divar_scraper.py
```

---

## 🔐 Authentication (Required for Phone Numbers)

Divar requires a login to display phone numbers. To save your session:

```python
# save_auth.py — run this once
import asyncio
from playwright.async_api import async_playwright

async def save():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe"
        )
        context = await browser.new_context()
        page = await context.new_page()
        await page.goto("https://divar.ir")
        input("Log in via the browser, then press Enter...")
        await context.storage_state(path="divar_auth.json")
        await browser.close()
        print("✅ Session saved to divar_auth.json")

asyncio.run(save())
```

After saving `divar_auth.json` in the same directory as the scraper, phone numbers will be retrieved automatically.

> If `divar_auth.json` does not exist, the scraper will still run without errors — phone numbers simply won't be shown.

---

## 📁 Output Structure

```
project/
├── divar_scraper.py
├── divar_auth.json        ← authentication session (optional)
│
├── images/
│   ├── ad_001/
│   │   ├── image_01.jpg
│   │   ├── image_02.jpg
│   │   └── ...
│   ├── ad_002/
│   │   └── image_01.jpg
│   └── ...
│
├── divar_ads.csv          ← CSV output
└── ads_report.txt         ← text report
```

### Sample CSV Output

| title | phone | link | image_count | image_files |
|-------|-------|------|-------------|-------------|
| 80m² Apartment | 09121234567 | https://divar.ir/v/... | 3 | ad_001/image_01.jpg \| ad_001/image_02.jpg |

### Sample Text Report (`ads_report.txt`)

```
================================================================================
                              DIVAR ADS REPORT
================================================================================

Ad #1
  Title      : 80m² Apartment in Tehran
  Phone      : 09121234567
  Link       : https://divar.ir/v/xxxxxxxx
  Images     : 3
  Files      : ad_001/image_01.jpg | ad_001/image_02.jpg | ad_001/image_03.jpg
────────────────────────────────────────────────────────────────────────────────
```

---

## ⚙️ Configuration

At the top of `divar_scraper.py`:

| Variable | Default | Description |
|----------|---------|-------------|
| `MY_AD_LINKS` | `[]` | List of listing URLs |
| `MAX_IMAGES` | `8` | Maximum number of images per listing |
| `executable_path` | Chrome path | Path to Chrome on your system |

---

## 🔬 Technical Details

### Why don't we click on thumbnails?

Clicking carousel thumbnail buttons on Divar opens a **fullscreen viewer** that disrupts the scraper's flow. The solution: Divar keeps all images **loaded in the DOM simultaneously**:

```html
<div class="kt-base-carousel__slide">
  <picture>
    <source srcset="https://...jpg">
    <img src="https://...jpg" class="kt-image-block__image">
  </picture>
</div>
```

The scraper reads the `src` and `srcset` attributes directly from all slides in the DOM — no interaction needed.

### Image Extraction Priority

```
1️⃣  img inside  .kt-base-carousel__slide        ← primary method
2️⃣  source > picture  inside the carousel       ← if img is empty
3️⃣  any img with a Divar URL on the page        ← final fallback
```

---

## ⚠️ Important Notes

- This tool is designed for **personal use**.
- There is a **3-second delay** between each listing to reduce load on Divar's servers.
- Commercial use or bulk scraping may violate **Divar's Terms of Service**.

---

## 🛠️ Dependencies

| Library | Role |
|---------|------|
| `playwright` | Browser control and page rendering |
| `aiohttp` | Async image downloading |
| `aiofiles` | Async file writing |

---
