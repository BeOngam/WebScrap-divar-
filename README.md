# 🕷️ Divar Scraper

اسکرپر async برای استخراج اطلاعات آگهی‌های [دیوار](https://divar.ir) — عنوان، شماره تماس و تمام تصاویر هر آگهی — با خروجی مرتب در CSV، گزارش متنی و پوشه‌بندی تصاویر.

---

## ✨ قابلیت‌ها

- استخراج **عنوان** آگهی
- دریافت **شماره تماس** با کلیک خودکار روی دکمه «نمایش شماره»
- دانلود تا **۸ تصویر** از هر آگهی — مستقیم از DOM، **بدون کلیک روی carousel**
- ذخیره خروجی در **CSV** و **گزارش متنی**
- پوشه‌بندی تصاویر به صورت `images/ad_001/image_01.jpg`
- پشتیبانی از **session احراز هویت** دیوار (برای دسترسی به شماره‌ها)
- مدیریت خطا: اگر یک آگهی خطا داد، بقیه ادامه پیدا می‌کنند

---

## 📋 پیش‌نیازها

- Python 3.10+
- Google Chrome نصب‌شده روی سیستم
- کتابخانه‌های زیر:

```bash
pip install playwright aiohttp aiofiles
playwright install chromium
```

---

## 🚀 نحوه استفاده

### ۱. لینک‌های آگهی را وارد کنید

فایل `divar_scraper.py` را باز کنید و لینک‌های مورد نظر را در لیست `MY_AD_LINKS` قرار دهید:

```python
MY_AD_LINKS = [
    "https://divar.ir/v/xxxxxxxx",
    "https://divar.ir/v/yyyyyyyy",
    # ...
]
```

### ۲. اسکرپر را اجرا کنید

```bash
python divar_scraper.py
```

---

## 🔐 احراز هویت (برای دریافت شماره تماس)

دیوار برای نمایش شماره تماس نیاز به لاگین دارد. برای ذخیره session:

```python
# save_auth.py — یک‌بار اجرا کنید
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
        input("در مرورگر لاگین کنید، سپس Enter بزنید...")
        await context.storage_state(path="divar_auth.json")
        await browser.close()
        print("✅ Session saved to divar_auth.json")

asyncio.run(save())
```

بعد از ذخیره `divar_auth.json` در کنار اسکرپر، شماره‌ها به صورت خودکار دریافت می‌شوند.

> اگر فایل `divar_auth.json` وجود نداشته باشد، اسکرپر بدون خطا اجرا می‌شود — فقط شماره‌ها نمایش داده نمی‌شوند.

---

## 📁 ساختار خروجی

```
project/
├── divar_scraper.py
├── divar_auth.json        ← session احراز هویت (اختیاری)
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
├── divar_ads.csv          ← خروجی CSV
└── ads_report.txt         ← گزارش متنی
```

### نمونه خروجی CSV

| title | phone | link | image_count | image_files |
|-------|-------|------|-------------|-------------|
| آپارتمان ۸۰ متری | 09121234567 | https://divar.ir/v/... | 3 | ad_001/image_01.jpg \| ad_001/image_02.jpg |

### نمونه گزارش متنی (`ads_report.txt`)

```
================================================================================
                              DIVAR ADS REPORT
================================================================================

Ad #1
  Title      : آپارتمان ۸۰ متری در تهران
  Phone      : 09121234567
  Link       : https://divar.ir/v/xxxxxxxx
  Images     : 3
  Files      : ad_001/image_01.jpg | ad_001/image_02.jpg | ad_001/image_03.jpg
────────────────────────────────────────────────────────────────────────────────
```

---

## ⚙️ تنظیمات

در ابتدای فایل `divar_scraper.py`:

| متغیر | پیش‌فرض | توضیح |
|-------|---------|-------|
| `MY_AD_LINKS` | `[]` | لیست لینک‌های آگهی |
| `MAX_IMAGES` | `8` | حداکثر تعداد تصویر به ازای هر آگهی |
| `executable_path` | مسیر Chrome | مسیر Chrome روی سیستم شما |

---

## 🔬 جزئیات فنی

### چرا روی thumbnail کلیک نمی‌کنیم؟

دیوار با کلیک روی thumbnail دکمه‌های carousel، یک **fullscreen viewer** باز می‌کند که flow اسکرپر را خراب می‌کند. راه‌حل: دیوار تمام تصاویر را **همزمان در DOM** نگه می‌دارد:

```html
<div class="kt-base-carousel__slide">
  <picture>
    <source srcset="https://...jpg">
    <img src="https://...jpg" class="kt-image-block__image">
  </picture>
</div>
```

اسکرپر مستقیم `src` و `srcset` همه slide ها را از DOM می‌خواند — بدون هیچ interaction.

### ترتیب اولویت استخراج تصویر

```
1️⃣  img داخل  .kt-base-carousel__slide        ← روش اصلی
2️⃣  source > picture  داخل carousel           ← اگر img خالی بود
3️⃣  هر img با URL دیوار در صفحه               ← fallback نهایی
```

---

## ⚠️ نکات مهم

- این ابزار برای **استفاده شخصی** طراحی شده است.
- بین هر آگهی **۳ ثانیه تأخیر** وجود دارد تا فشار روی سرور دیوار کم باشد.
- استفاده تجاری یا scraping انبوه ممکن است با **شرایط استفاده دیوار** مغایرت داشته باشد.

---

## 🛠️ وابستگی‌ها

| کتابخانه | نقش |
|----------|-----|
| `playwright` | کنترل مرورگر و رندر صفحه |
| `aiohttp` | دانلود async تصاویر |
| `aiofiles` | نوشتن async فایل |

---

## 📄 لایسنس

MIT
