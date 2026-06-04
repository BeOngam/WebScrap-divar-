import asyncio
import csv
import os
import re
import aiohttp
import aiofiles
from playwright.async_api import async_playwright

# ========== لینک‌های مورد نظر خود را اینجا وارد کنید ==========
MY_AD_LINKS = [
    "https://divar.ir/v/gaTMhkQy",
    "https://divar.ir/v/QawjqMMQ",
    "https://divar.ir/v/gaTQhuca",
    # هر لینک دیگری را اضافه کنید
]
# =========================================================


async def download_image(session: aiohttp.ClientSession, url: str, file_path: str) -> bool:
    """دانلود یک تصویر و ذخیره در فایل"""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Referer": "https://divar.ir/",
    }
    try:
        async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=20)) as resp:
            if resp.status == 200:
                async with aiofiles.open(file_path, mode="wb") as f:
                    await f.write(await resp.read())
                return True
            else:
                print(f"      ⚠️ HTTP {resp.status} for {url}")
    except Exception as e:
        print(f"      ❌ Download error: {e}")
    return False


def _normalize_url(src: str | None) -> str | None:
    if not src:
        return None
    src = src.strip()
    if src.startswith("//"):
        src = "https:" + src
    elif src.startswith("/"):
        src = "https://divar.ir" + src
    return src if src.startswith("http") else None


def _is_real_image(url: str) -> bool:
    """تصاویر واقعی را از آیکون و placeholder جدا می‌کند"""
    low = url.lower()
    junk = ("icon", "logo", "avatar", "placeholder", "loading", "spinner", "favicon")
    return not any(j in low for j in junk)


def _get_high_res_url(url: str) -> str:
    """
    تبدیل URL تصویر کوچک به تصویر بزرگ.
    دیوار معمولاً از پارامتر s= یا /-/ برای resize استفاده می‌کند.
    """
    # حذف پارامترهای resize مثل ?s=200x200
    url = re.sub(r'\?.*$', '', url)
    # تبدیل thumbnail به original اگر در path وجود دارد
    url = url.replace('/thumbnail/', '/').replace('/thumb/', '/')
    return url


async def get_all_image_urls(page) -> list[str]:
    """
    استخراج URL تمام تصاویر آگهی از دیوار
    بدون کلیک روی هیچ المنتی - فقط از DOM و source های موجود.
    """

    # ── روش اول: استخراج از thumbnail button ها بدون کلیک ──────────────
    # aria-label مثل "تصویر 2 از 5" به ما تعداد می‌دهد
    image_urls: list[str] = []

    # تعداد کل تصاویر را از aria-label بخوان
    total_images = 0
    try:
        buttons = await page.locator(
            "button.kt-base-carousel__thumbnail-button"
        ).all()
        total_images = len(buttons)
        print(f"   🔢 Thumbnail buttons found: {total_images}")

        # از هر button، background-image یا img src داخلش بگیر
        for btn in buttons:
            try:
                # img داخل button
                img = btn.locator("img").first
                if await img.count() > 0:
                    for attr in ("src", "data-src", "data-lazy-src"):
                        src = await img.get_attribute(attr)
                        if src:
                            src = _normalize_url(src)
                            if src and _is_real_image(src):
                                src = _get_high_res_url(src)
                                if src not in image_urls:
                                    image_urls.append(src)
                                break
            except Exception:
                continue
    except Exception as e:
        print(f"   ⚠️ thumbnail button extraction error: {e}")

    # ── روش دوم: img های داخل slide ها (بدون trigger کلیک) ──────────────
    if not image_urls:
        try:
            slide_imgs = await page.locator(
                "div.kt-base-carousel__slides img, "
                "div[class*='carousel__slide'] img, "
                "div[class*='swiper-slide'] img, "
                "div.post-page__images img"
            ).all()
            for img in slide_imgs:
                try:
                    for attr in ("src", "data-src", "data-lazy-src", "data-original"):
                        src = await img.get_attribute(attr)
                        if src:
                            src = _normalize_url(src)
                            if src and _is_real_image(src):
                                src = _get_high_res_url(src)
                                if src not in image_urls:
                                    image_urls.append(src)
                                break
                except Exception:
                    continue
        except Exception as e:
            print(f"   ⚠️ slide img extraction error: {e}")

    # ── روش سوم: JavaScript - بدون trigger کلیک ─────────────────────────
    if not image_urls:
        try:
            srcs: list = await page.evaluate("""
                () => {
                    const results = new Set();

                    // همه img هایی که به نظر می‌رسند آگهی باشند
                    document.querySelectorAll('img').forEach(img => {
                        const attrs = ['src', 'data-src', 'data-lazy-src', 'data-original'];
                        for (const attr of attrs) {
                            const val = img.getAttribute(attr);
                            if (val && val.startsWith('http') && 
                                !val.includes('icon') && !val.includes('logo') &&
                                !val.includes('avatar') && !val.includes('spinner')) {
                                results.add(val);
                            }
                        }
                    });

                    // srcset هم بررسی کن و بزرگترین را بگیر
                    document.querySelectorAll('img[srcset], source[srcset]').forEach(el => {
                        const srcset = el.getAttribute('srcset') || '';
                        const parts = srcset.split(',').map(s => s.trim());
                        parts.forEach(part => {
                            const url = part.split(/\\s+/)[0];
                            if (url && url.startsWith('http')) {
                                results.add(url);
                            }
                        });
                    });

                    return [...results].filter(url => 
                        url.match(/\\.(jpg|jpeg|png|webp)(\\?|$)/i) ||
                        url.includes('/pictures/') ||
                        url.includes('/images/')
                    );
                }
            """)
            for src in srcs:
                src = _normalize_url(src)
                if src and _is_real_image(src):
                    src = _get_high_res_url(src)
                    if src not in image_urls:
                        image_urls.append(src)
        except Exception as e:
            print(f"   ⚠️ JS extraction error: {e}")

    # ── روش چهارم: network response intercept (اگر هنوز خالی است) ───────
    # این روش قبلاً در page navigation انجام می‌شود - به تابع scrape_ad نگاه کن

    print(f"   📷 Total unique image URLs found: {len(image_urls)}")
    return image_urls[:10]  # حداکثر ۱۰ تصویر


async def get_phone_number(page) -> str:
    """
    دریافت شماره تماس از صفحه آگهی دیوار.
    دکمه 'نمایش شماره' را کلیک می‌کند و شماره را استخراج می‌کند.
    """
    phone = "Phone not available"

    btn_selectors = [
        "button.kt-button.post-actions__get-contact",
        "button[class*='get-contact']",
        "button[class*='contact']",
        "div.post-actions button",
        "button.cta-btn--contact",
    ]
    clicked = False
    for sel in btn_selectors:
        try:
            btn = page.locator(sel).first
            if await btn.count() > 0:
                await btn.click(timeout=4000)
                clicked = True
                break
        except Exception:
            continue

    if not clicked:
        return phone

    await page.wait_for_timeout(1500)

    # ── روش ۱: تگ <a href="tel:..."> ──────────────────────────────────
    try:
        tel = page.locator('a[href^="tel:"]').first
        if await tel.count() > 0:
            href = await tel.get_attribute("href") or ""
            phone = href.replace("tel:", "").strip()
            if phone:
                return phone
    except Exception:
        pass

    # ── روش ۲: متن با فرمت شماره موبایل ایران ──────────────────────────
    try:
        el = await page.wait_for_selector("text=/0[0-9]{10}/", timeout=2500)
        if el:
            raw = await el.text_content() or ""
            match = re.search(r"0[0-9]{10}", raw)
            if match:
                return match.group()
    except Exception:
        pass

    # ── روش ۳: هر متنی که شبیه شماره است ───────────────────────────────
    try:
        content = await page.content()
        match = re.search(r'\b(09[0-9]{9}|0[1-8][0-9]{9})\b', content)
        if match:
            return match.group()
    except Exception:
        pass

    return phone


async def scrape_ad(
    page,
    ad_link: str,
    idx: int,
    session: aiohttp.ClientSession,
    captured_urls: list[str],
) -> dict:
    """
    پردازش کامل یک آگهی: باز کردن صفحه، دریافت اطلاعات و دانلود تصاویر.
    captured_urls: لیستی که توسط network interceptor پر می‌شود.
    """
    print(f"\n🔄 [{idx+1}] {ad_link}")

    captured_urls.clear()

    await page.goto(ad_link, wait_until="domcontentloaded", timeout=30000)
    # صبر برای بارگذاری تصاویر lazy - بدون اسکرول که باعث باز شدن تصویر می‌شود
    await page.wait_for_timeout(3000)

    # ── عنوان ────────────────────────────────────────────────────────────
    title = "Unknown"
    title_selectors = [
        "h1.kt-page-title__title",
        "h1[class*='title']",
        "h1",
    ]
    for sel in title_selectors:
        try:
            el = page.locator(sel).first
            if await el.count() > 0:
                title = (await el.text_content() or "").strip()
                if title:
                    break
        except Exception:
            continue

    if not title or title == "دیوار":
        title = (await page.title() or f"Ad {idx+1}").strip()

    # ── شماره تماس ───────────────────────────────────────────────────────
    phone = await get_phone_number(page)

    # ── تصاویر - ابتدا از DOM، سپس از network capture ────────────────────
    image_urls = await get_all_image_urls(page)

    # اگر DOM خالی بود، از network interceptor استفاده کن
    if not image_urls and captured_urls:
        print(f"   🌐 Using {len(captured_urls)} network-captured URLs")
        image_urls = list(dict.fromkeys(captured_urls))[:10]

    print(f"   📷 Final: {len(image_urls)} image(s) | 📞 {phone}")

    # ── دانلود تصاویر ────────────────────────────────────────────────────
    ad_folder = os.path.join("images", f"ad_{idx+1:03d}")
    os.makedirs(ad_folder, exist_ok=True)

    local_filenames: list[str] = []
    for img_idx, img_url in enumerate(image_urls, start=1):
        ext = img_url.split(".")[-1].split("?")[0].lower()
        if ext not in ("jpg", "jpeg", "png", "webp"):
            ext = "jpg"
        filename = f"image_{img_idx:02d}.{ext}"
        filepath = os.path.join(ad_folder, filename)
        success = await download_image(session, img_url, filepath)
        if success:
            local_filenames.append(os.path.join(f"ad_{idx+1:03d}", filename))
            print(f"      ✅ Saved: {filename}")
        else:
            print(f"      ❌ Failed: {img_url}")

    if not local_filenames:
        print("      ⚠️  No images downloaded for this ad.")

    return {
        "title": title,
        "phone": phone,
        "link": ad_link,
        "image_count": len(local_filenames),
        "image_files": " | ".join(local_filenames),
    }


async def main():
    os.makedirs("images", exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            args=["--disable-blink-features=AutomationControlled"],
        )

        auth_file = "divar_auth.json"
        if os.path.exists(auth_file):
            context = await browser.new_context(
                storage_state=auth_file,
                viewport={"width": 1280, "height": 800},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
            )
            print("✔ Auth file loaded.")
        else:
            context = await browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
            )
            print("⚠️  No auth file found – phone numbers may not be accessible.")

        page = await context.new_page()

        # ── Network interceptor: فقط URL های تصاویر را ذخیره کن ──────────
        # این روش تصاویری را که مرورگر واقعاً load کرده capture می‌کند
        captured_image_urls: list[str] = []

        def handle_response(response):
            url = response.url
            content_type = response.headers.get("content-type", "")
            # فقط تصاویر واقعی صفحه آگهی
            if (
                "image" in content_type
                and _is_real_image(url)
                and "divar" in url
                and url not in captured_image_urls
            ):
                captured_image_urls.append(url)

        page.on("response", handle_response)

        full_ads: list[dict] = []

        async with aiohttp.ClientSession() as session:
            for idx, link in enumerate(MY_AD_LINKS):
                try:
                    ad_data = await scrape_ad(page, link, idx, session, captured_image_urls)
                    full_ads.append(ad_data)
                except Exception as e:
                    print(f"   💥 Error processing {link}: {e}")
                    full_ads.append({
                        "title": f"Error – Ad {idx+1}",
                        "phone": "N/A",
                        "link": link,
                        "image_count": 0,
                        "image_files": "",
                    })

                if idx < len(MY_AD_LINKS) - 1:
                    await asyncio.sleep(3)

        await browser.close()

    # ── ذخیره CSV ────────────────────────────────────────────────────────
    csv_file = "divar_ads.csv"
    fieldnames = ["title", "phone", "link", "image_count", "image_files"]
    with open(csv_file, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(full_ads)

    # ── ذخیره گزارش متنی ─────────────────────────────────────────────────
    txt_file = "ads_report.txt"
    with open(txt_file, "w", encoding="utf-8") as f:
        f.write("=" * 100 + "\n")
        f.write("DIVAR ADS REPORT".center(100) + "\n")
        f.write("=" * 100 + "\n\n")
        for i, ad in enumerate(full_ads, 1):
            f.write(f"Ad #{i}\n")
            f.write(f"Title      : {ad['title']}\n")
            f.write(f"Phone      : {ad['phone']}\n")
            f.write(f"Link       : {ad['link']}\n")
            f.write(f"Images     : {ad['image_count']}\n")
            f.write(f"Image Files: {ad['image_files']}\n")
            f.write("-" * 100 + "\n\n")

    print(f"\n{'='*60}")
    print(f"✅  CSV saved   → {csv_file}")
    print(f"📄  Report saved → {txt_file}")
    print(f"🖼️   Images saved → images/")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())