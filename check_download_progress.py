import json
from pathlib import Path

def check_progress():
    base_dir = Path("districts")
    if not base_dir.exists():
        print("districts folder does not exist.")
        return

    total_districts = 0
    total_talukas = 0
    total_pdfs = 0
    total_bytes = 0

    scraped_talukas = 0

    for d_dir in base_dir.iterdir():
        if d_dir.is_dir():
            total_districts += 1
            taluka_dir = d_dir / "talukas"
            pdf_dir = d_dir / "pdfs"
            
            if taluka_dir.exists():
                for tf in taluka_dir.glob("*.json"):
                    total_talukas += 1
                    try:
                        with open(tf, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            if data.get("scraped") or data.get("downloaded_pdfs") or data.get("last_checked_at"):
                                scraped_talukas += 1
                    except:
                        pass

            if pdf_dir.exists():
                for pf in pdf_dir.rglob("*.pdf"):
                    total_pdfs += 1
                    total_bytes += pf.stat().st_size

    print("=" * 60)
    print("MAHARASHTRA DP PDF DOWNLOAD PROGRESS REPORT")
    print("=" * 60)
    print(f"Districts Processed: {total_districts}")
    print(f"Talukas Checked:     {scraped_talukas} / {total_talukas}")
    print(f"Total PDFs Downloaded: {total_pdfs}")
    print(f"Total Disk Size:       {total_bytes / (1024*1024):.2f} MB")
    print("=" * 60)

if __name__ == "__main__":
    check_progress()
