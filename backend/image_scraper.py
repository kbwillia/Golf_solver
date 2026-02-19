import os
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

print("Starting image scraping with Selenium...")

BASE_URL = "https://www.masters.com/en_US/course/index.html"
SAVE_DIR = "static/masters_images"
os.makedirs(SAVE_DIR, exist_ok=True)

# Setup headless Chrome
options = Options()
options.add_argument("--headless")
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36")

print("Launching browser...")
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)

print(f"Navigating to {BASE_URL}")
driver.get(BASE_URL)
time.sleep(5)  # Wait for JS to render

html = driver.page_source
driver.quit()

print("Parsing rendered HTML...")
soup = BeautifulSoup(html, "html.parser")

imgs = soup.find_all("img")
print(f"Found {len(imgs)} <img> tags.")

count = 0
for i, img in enumerate(imgs):
    src = img.get("src")
    alt = img.get("alt", "").strip().replace(" ", "_").replace("/", "_")

    if not src:
        continue

    # Extract the base filename before extension
    base_name = os.path.splitext(os.path.basename(src))[0]

    # Build new filename with base name + alt text
    if alt:
        fname = f"{base_name}__{alt}.jpg"
    else:
        fname = f"{base_name}.jpg"

    # Clean filename
    fname = "".join(c for c in fname if c.isalnum() or c in ("_", "-", "."))

    img_url = urljoin(BASE_URL, src)
    print(f"Downloading {img_url} as {fname}")

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
        }
        img_data = requests.get(img_url, headers=headers, timeout=10)
        img_data.raise_for_status()

        file_path = os.path.join(SAVE_DIR, fname)
        with open(file_path, "wb") as f:
            f.write(img_data.content)

        print(f"Saved: {fname}")
        count += 1
    except Exception as e:
        print(f"Failed to download {img_url}: {e}")

print(f"\nDone: saved {count} images to {SAVE_DIR}")
