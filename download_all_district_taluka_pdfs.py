"""
Maharashtra DP PDF Downloader - Selenium Browser Edition
=========================================================
Uses a real Chrome browser (via Selenium) to load each taluka page,
wait for JavaScript to render, then find and download all PDFs.

Features:
- Real Chrome browser (headless) with full JS rendering
- Auto-downloads ChromeDriver via webdriver-manager
- One browser instance, navigates to each taluka page sequentially
- Waits up to 3 minutes per page load (government site is very slow)
- Skips talukas that already have downloaded PDFs
- Saves PDFs to districts/<district>/pdfs/<taluka>/
- Updates taluka JSON metadata after each download
- Live terminal progress output
"""

import sys
import os
import json
import re
import time
import requests
import urllib3
from pathlib import Path
from urllib.parse import urljoin

# Selenium imports
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# Fix Windows console encoding
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ─── CONFIG ──────────────────────────────────────────────────────────────
BASE_URL = "https://dtp.maharashtra.gov.in/home/downloads/dp/"
PAGE_LOAD_TIMEOUT = 180  # 3 minutes max per page (site is very slow)
PDF_DOWNLOAD_TIMEOUT = 120  # 2 minutes per PDF file download

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
}


def sanitize_filename(name):
    """Create a safe filename from a string."""
    clean = re.sub(r'[\\/:*?"<>|]', '_', name)
    clean = re.sub(r'\s+', '_', clean).strip('_')
    return clean if clean else "document"


def create_driver():
    """Create a headless Chrome WebDriver."""
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--ignore-certificate-errors")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-images")  # Faster loading
    chrome_options.add_argument(f"--user-agent={HEADERS['User-Agent']}")
    
    # Suppress logging
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])

    print("Setting up ChromeDriver...")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
    print("ChromeDriver ready!\n")
    return driver


def extract_pdf_links(driver):
    """Extract all PDF and map image links from the current page."""
    pdf_links = []
    
    try:
        # Wait for the styled-table to appear (up to 30 seconds after page load)
        try:
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "table.styled-table, table"))
            )
        except:
            pass  # Table might not exist for this taluka
        
        # Find all links in tables
        tables = driver.find_elements(By.TAG_NAME, "table")
        for table in tables:
            links = table.find_elements(By.TAG_NAME, "a")
            for link in links:
                try:
                    href = link.get_attribute("href")
                    if href and (".pdf" in href.lower() or "wp-content/uploads" in href.lower()):
                        title = link.text.strip() or Path(href).name
                        # Get parent row text for context
                        try:
                            row = link.find_element(By.XPATH, "./ancestor::tr")
                            cells = row.find_elements(By.TAG_NAME, "td")
                            context = [c.text.strip()[:60] for c in cells]
                        except:
                            context = []
                        
                        pdf_links.append({
                            "title": title,
                            "url": href,
                            "context": context
                        })
                except:
                    continue
        
        # Also search the entire page for PDF links NOT in tables
        all_links = driver.find_elements(By.TAG_NAME, "a")
        table_urls = {p["url"] for p in pdf_links}
        for link in all_links:
            try:
                href = link.get_attribute("href")
                if href and href not in table_urls:
                    if ".pdf" in href.lower() and "wp-content/uploads" in href.lower():
                        title = link.text.strip() or Path(href).name
                        pdf_links.append({
                            "title": title,
                            "url": href,
                            "context": []
                        })
            except:
                continue
    except Exception as e:
        print(f"    Error extracting links: {e}")
    
    return pdf_links


def download_file(url, target_file):
    """Download a file using requests (faster than Selenium for binary files)."""
    session = requests.Session()
    session.headers.update(HEADERS)
    
    try:
        r = session.get(url, verify=False, timeout=PDF_DOWNLOAD_TIMEOUT, stream=True)
        if r.status_code == 200:
            with open(target_file, "wb") as f:
                for chunk in r.iter_content(chunk_size=16384):
                    if chunk:
                        f.write(chunk)
            return target_file.stat().st_size
        else:
            return -1
    except Exception as e:
        print(f"    Download error: {e}")
        return -1


def process_taluka(driver, district_id, district_name, taluka_id, taluka_name, json_file, pdf_dir):
    """Navigate to taluka page, extract PDF links, download files."""
    
    # Use the ORIGINAL taluka name (not sanitized ID) for the URL parameter
    # The site uses the exact name from cityTalukaMap as the tal= parameter
    target_url = f"{BASE_URL}?cities={district_id}&tal={taluka_name}&languages="
    
    # Try loading the page
    try:
        driver.get(target_url)
        # Give extra time for slow JS rendering
        time.sleep(3)
    except Exception as e:
        # Timeout - try once more with the sanitized ID version
        try:
            alt_url = f"{BASE_URL}?cities={district_id}&tal={taluka_id}&languages="
            driver.get(alt_url)
            time.sleep(3)
            target_url = alt_url
        except:
            return {
                "status": "page_load_failed",
                "pdfs_downloaded": 0,
                "bytes_downloaded": 0,
                "error": str(e)
            }
    
    # Extract PDF links from the rendered page
    pdf_links = extract_pdf_links(driver)
    
    # Download each PDF
    pdf_dir.mkdir(parents=True, exist_ok=True)
    download_records = []
    taluka_bytes = 0
    
    for idx, pdf_item in enumerate(pdf_links, 1):
        pdf_url = pdf_item["url"]
        pdf_title = pdf_item["title"]
        
        # Create safe filename
        safe_fname = sanitize_filename(pdf_title)
        ext = Path(pdf_url).suffix if Path(pdf_url).suffix else ".pdf"
        if not safe_fname.lower().endswith(ext.lower()):
            safe_fname += ext
        
        target_file = pdf_dir / safe_fname
        if target_file.exists():
            safe_fname = f"{idx}_{safe_fname}"
            target_file = pdf_dir / safe_fname
        
        rec = {
            "title": pdf_title,
            "online_url": pdf_url,
            "local_file": str(target_file.as_posix()),
            "status": "pending"
        }
        
        file_size = download_file(pdf_url, target_file)
        if file_size > 0:
            rec["status"] = "downloaded"
            rec["size_bytes"] = file_size
            rec["downloaded_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
            taluka_bytes += file_size
            print(f"      Downloaded: {safe_fname} ({file_size/1024:.1f} KB)")
        else:
            rec["status"] = "failed"
        
        download_records.append(rec)
    
    # Update taluka JSON metadata
    if json_file.exists():
        try:
            with open(json_file, "r", encoding="utf-8") as jf:
                jdata = json.load(jf)
        except:
            jdata = {}
    else:
        jdata = {}
    
    jdata.update({
        "district_id": district_id,
        "district_name": district_name,
        "taluka_id": taluka_id,
        "taluka_name": taluka_name,
        "query_url": target_url,
        "last_checked_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "pdf_storage_dir": str(pdf_dir.as_posix()),
        "pdfs_found": len(pdf_links),
        "downloaded_pdfs": download_records
    })
    
    json_file.parent.mkdir(parents=True, exist_ok=True)
    with open(json_file, "w", encoding="utf-8") as jf:
        json.dump(jdata, jf, indent=2, ensure_ascii=False)
    
    return {
        "status": "success",
        "pdfs_downloaded": len([r for r in download_records if r["status"] == "downloaded"]),
        "bytes_downloaded": taluka_bytes
    }


def should_skip(json_file):
    """Check if a taluka has already been successfully processed."""
    if not json_file.exists():
        return False
    try:
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Skip if already checked AND has downloaded PDFs (or confirmed 0 PDFs)
        if data.get("last_checked_at") and "downloaded_pdfs" in data:
            downloaded = [p for p in data["downloaded_pdfs"] if p.get("status") == "downloaded"]
            if len(downloaded) > 0:
                return True  # Has PDFs already downloaded - skip
        return False
    except:
        return False


def main():
    index_path = Path("districts/index.json")
    if not index_path.exists():
        print("ERROR: districts/index.json not found!")
        print("Run generate_proper_folder_structure.py first.")
        return
    
    with open(index_path, "r", encoding="utf-8") as f:
        master_index = json.load(f)
    
    # Build taluka queue
    taluka_queue = []
    skipped = 0
    for district in master_index:
        d_id = district["district_id"]
        d_name = district["district_name"]
        for taluka in district["talukas"]:
            t_id = taluka["taluka_id"]
            t_name = taluka["taluka_name"]
            json_file = Path(taluka["json_file"])
            safe_t_id = re.sub(r'[\\/:*?"<>|]', '_', t_id)
            pdf_dir = Path(f"districts/{d_id}/pdfs/{safe_t_id}")
            
            if should_skip(json_file):
                skipped += 1
                continue
            
            taluka_queue.append({
                "district_id": d_id,
                "district_name": d_name,
                "taluka_id": t_id,
                "taluka_name": t_name,
                "json_file": json_file,
                "pdf_dir": pdf_dir
            })
    
    total = len(taluka_queue)
    print("=" * 70)
    print("MAHARASHTRA DP PDF DOWNLOADER - SELENIUM BROWSER EDITION")
    print("=" * 70)
    print(f"Total talukas to process: {total}")
    print(f"Already downloaded (skipped): {skipped}")
    print(f"Page load timeout: {PAGE_LOAD_TIMEOUT}s per page")
    print("=" * 70)
    
    if total == 0:
        print("\nAll talukas already processed! Nothing to do.")
        return
    
    # Create browser
    driver = create_driver()
    
    completed = 0
    total_pdfs = 0
    total_bytes = 0
    errors = 0
    
    try:
        for item in taluka_queue:
            completed += 1
            d_id = item["district_id"]
            t_name = item["taluka_name"]
            
            print(f"\n[{completed}/{total}] {d_id} -> {t_name}")
            print(f"    URL: {BASE_URL}?cities={d_id}&tal={t_name}&languages=")
            
            try:
                result = process_taluka(
                    driver,
                    item["district_id"],
                    item["district_name"],
                    item["taluka_id"],
                    item["taluka_name"],
                    item["json_file"],
                    item["pdf_dir"]
                )
                
                pdfs = result["pdfs_downloaded"]
                bytes_dl = result["bytes_downloaded"]
                total_pdfs += pdfs
                total_bytes += bytes_dl
                
                if result["status"] == "success":
                    print(f"    Result: {pdfs} PDFs ({bytes_dl/1024:.1f} KB)")
                else:
                    print(f"    Result: FAILED - {result.get('error', 'unknown')}")
                    errors += 1
                    
            except Exception as exc:
                print(f"    ERROR: {exc}")
                errors += 1
                # Restart browser if it crashed
                try:
                    driver.current_url
                except:
                    print("    Browser crashed - restarting...")
                    try:
                        driver.quit()
                    except:
                        pass
                    driver = create_driver()
            
            # Progress summary every 10 talukas
            if completed % 10 == 0:
                print(f"\n--- Progress: {completed}/{total} done | {total_pdfs} PDFs | {total_bytes/(1024*1024):.2f} MB | {errors} errors ---\n")
    
    finally:
        try:
            driver.quit()
        except:
            pass
    
    # Final summary
    print("\n" + "=" * 70)
    print("DOWNLOAD COMPLETE")
    print("=" * 70)
    print(f"Talukas processed:    {completed}")
    print(f"Total PDFs downloaded: {total_pdfs}")
    print(f"Total data:           {total_bytes/(1024*1024):.2f} MB")
    print(f"Errors:               {errors}")
    print("=" * 70)


if __name__ == "__main__":
    main()
