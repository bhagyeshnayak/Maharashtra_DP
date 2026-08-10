import json
import time
from pathlib import Path

def monitor():
    base_dir = Path("districts")
    print("=" * 60)
    print("LIVE MAHARASHTRA DP PDF DOWNLOAD MONITOR")
    print("Press Ctrl+C to stop monitoring.")
    print("=" * 60)

    try:
        while True:
            total_pdfs = 0
            total_bytes = 0
            scraped_talukas = 0
            total_talukas = 0

            for d_dir in base_dir.iterdir():
                if d_dir.is_dir():
                    taluka_dir = d_dir / "talukas"
                    pdf_dir = d_dir / "pdfs"
                    
                    if taluka_dir.exists():
                        for tf in taluka_dir.glob("*.json"):
                            total_talukas += 1
                            try:
                                with open(tf, "r", encoding="utf-8") as f:
                                    data = json.load(f)
                                    if data.get("downloaded_pdfs") or data.get("last_checked_at"):
                                        scraped_talukas += 1
                            except:
                                pass

                    if pdf_dir.exists():
                        for pf in pdf_dir.rglob("*.*"):
                            if pf.is_file() and not pf.name.endswith(".json"):
                                total_pdfs += 1
                                total_bytes += pf.stat().st_size

            timestamp = time.strftime("%H:%M:%S")
            print(f"[{timestamp}] Checked: {scraped_talukas}/{total_talukas} Talukas | Downloaded: {total_pdfs} PDFs | Total Size: {total_bytes / (1024*1024):.2f} MB")
            time.sleep(3)
    except KeyboardInterrupt:
        print("\nMonitoring stopped.")

if __name__ == "__main__":
    monitor()
