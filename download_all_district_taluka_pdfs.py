import sys
import json
import re
import time
import requests
import urllib3
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = "https://dtp.maharashtra.gov.in/home/downloads/dp/"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9"
}

TIMEOUT = 60
MAX_RETRIES = 3

def sanitize_filename(name):
    clean = re.sub(r'[\/\\:\*\?"<>\|]', '_', name)
    clean = re.sub(r'\s+', '_', clean).strip('_')
    return clean if clean else "document"

def process_single_taluka(item):
    d_id = item["district_id"]
    d_name = item["district_name"]
    t_id = item["taluka_id"]
    t_name = item["taluka_name"]
    jpath = item["json_file"]
    pdir = item["pdf_dir"]

    target_url = f"{BASE_URL}?cities={d_id}&tal={t_id}&languages="
    
    session = requests.Session()
    session.headers.update(HEADERS)

    html_text = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = session.get(target_url, verify=False, timeout=TIMEOUT)
            if resp.status_code == 200:
                html_text = resp.text
                break
        except Exception as req_err:
            time.sleep(1)

    if not html_text:
        return {
            "district_id": d_id,
            "taluka_id": t_id,
            "taluka_name": t_name,
            "status": "failed_fetch",
            "pdfs_downloaded": 0,
            "bytes_downloaded": 0
        }

    soup = BeautifulSoup(html_text, "html.parser")
    tables = soup.find_all("table")

    pdf_links = []
    for table in tables:
        rows = table.find_all("tr")
        for row in rows:
            cols = row.find_all(["td", "th"])
            col_texts = [c.get_text(" ", strip=True) for c in cols]

            for a in row.find_all("a", href=True):
                href = a["href"]
                if ".pdf" in href.lower() or "wp-content/uploads" in href.lower():
                    full_url = urljoin(BASE_URL, href)
                    link_title = a.get_text(strip=True) or Path(href).name
                    pdf_links.append({
                        "title": link_title,
                        "url": full_url,
                        "context": col_texts
                    })

    pdir.mkdir(parents=True, exist_ok=True)
    download_records = []
    taluka_bytes = 0

    for p_idx, pdf_item in enumerate(pdf_links, 1):
        pdf_url = pdf_item["url"]
        pdf_title = pdf_item["title"]
        
        safe_fname = sanitize_filename(pdf_title)
        ext = Path(pdf_url).suffix if Path(pdf_url).suffix else ".pdf"
        if not safe_fname.lower().endswith(ext.lower()):
            safe_fname += ext

        target_file = pdir / safe_fname
        if target_file.exists():
            safe_fname = f"{p_idx}_{safe_fname}"
            target_file = pdir / safe_fname

        rec = {
            "title": pdf_title,
            "online_url": pdf_url,
            "local_file": str(target_file.as_posix()),
            "status": "pending"
        }

        try:
            r = session.get(pdf_url, verify=False, timeout=90, stream=True)
            if r.status_code == 200:
                with open(target_file, "wb") as pf:
                    for chunk in r.iter_content(chunk_size=16384):
                        if chunk:
                            pf.write(chunk)
                
                fsize = target_file.stat().st_size
                rec["status"] = "downloaded"
                rec["size_bytes"] = fsize
                rec["downloaded_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
                taluka_bytes += fsize
            else:
                rec["status"] = f"http_{r.status_code}"
        except Exception as dl_err:
            rec["status"] = f"error: {dl_err}"

        download_records.append(rec)

    # Update Taluka JSON
    if jpath.exists():
        try:
            with open(jpath, "r", encoding="utf-8") as jf:
                jdata = json.load(jf)
        except:
            jdata = {}
    else:
        jdata = {}

    jdata.update({
        "district_id": d_id,
        "district_name": d_name,
        "taluka_id": t_id,
        "taluka_name": t_name,
        "query_url": target_url,
        "last_checked_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "pdf_storage_dir": str(pdir.as_posix()),
        "pdfs_found": len(pdf_links),
        "downloaded_pdfs": download_records
    })

    with open(jpath, "w", encoding="utf-8") as jf:
        json.dump(jdata, jf, indent=2, ensure_ascii=False)

    return {
        "district_id": d_id,
        "taluka_id": t_id,
        "taluka_name": t_name,
        "status": "success",
        "pdfs_downloaded": len([r for r in download_records if r["status"] == "downloaded"]),
        "bytes_downloaded": taluka_bytes
    }

def main(max_workers=5):
    index_path = Path("districts/index.json")
    if not index_path.exists():
        print("districts/index.json not found!")
        return

    with open(index_path, "r", encoding="utf-8") as f:
        master_index = json.load(f)

    taluka_queue = []
    for district in master_index:
        d_id = district["district_id"]
        d_name = district["district_name"]
        for taluka in district["talukas"]:
            t_id = taluka["taluka_id"]
            t_name = taluka["taluka_name"]
            json_file = Path(taluka["json_file"])
            safe_t_id = re.sub(r'[\/\\:\*\?"<>\|]', '_', t_id)
            pdf_dir = Path(f"districts/{d_id}/pdfs/{safe_t_id}")

            taluka_queue.append({
                "district_id": d_id,
                "district_name": d_name,
                "taluka_id": t_id,
                "taluka_name": t_name,
                "json_file": json_file,
                "pdf_dir": pdf_dir
            })

    total_talukas = len(taluka_queue)
    print("=" * 70)
    print(f"HIGH-SPEED CONCURRENT MAHARASHTRA PDF DOWNLOADER ({total_talukas} TALUKAS)")
    print(f"Concurrency: {max_workers} parallel workers")
    print("=" * 70)

    completed = 0
    total_pdfs = 0
    total_bytes = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_item = {
            executor.submit(process_single_taluka, item): item
            for item in taluka_queue
        }

        for future in as_completed(future_to_item):
            completed += 1
            item = future_to_item[future]
            try:
                res = future.result()
                total_pdfs += res["pdfs_downloaded"]
                total_bytes += res["bytes_downloaded"]
                print(f"[{completed}/{total_talukas}] COMPLETED: {res['district_id']} -> {res['taluka_name']} | Downloaded: {res['pdfs_downloaded']} PDFs ({res['bytes_downloaded'] / (1024*1024):.2f} MB)")
            except Exception as exc:
                print(f"[{completed}/{total_talukas}] ERROR on {item['district_id']} -> {item['taluka_name']}: {exc}")

    print("\n" + "=" * 70)
    print("ALL DISTRICT & TALUKA PDF DOWNLOADS FINISHED")
    print(f"Total PDFs Downloaded: {total_pdfs}")
    print(f"Total Data Downloaded: {total_bytes / (1024*1024):.2f} MB")
    print("=" * 70)

if __name__ == "__main__":
    main(max_workers=5)
