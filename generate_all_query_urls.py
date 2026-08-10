import json
import re
from pathlib import Path

BASE_URL = "https://dtp.maharashtra.gov.in/home/downloads/dp/"

def generate_query_urls():
    index_file = Path("districts/index.json")
    if not index_file.exists():
        print("districts/index.json not found!")
        return

    with open(index_file, "r", encoding="utf-8") as f:
        master_index = json.load(f)

    all_urls = []
    total_query_urls = 0

    print("Generating query URLs for all Districts and Talukas...")

    for district in master_index:
        d_id = district["district_id"]
        d_name = district["district_name"]
        
        # District level query URL
        district_url = f"{BASE_URL}?cities={d_id}"
        
        # Load district.json
        d_json_path = Path(district["district_file"])
        if d_json_path.exists():
            with open(d_json_path, "r", encoding="utf-8") as df:
                d_data = json.load(df)
            d_data["query_url"] = district_url
            with open(d_json_path, "w", encoding="utf-8") as df:
                json.dump(d_data, df, indent=2, ensure_ascii=False)

        for taluka in district["talukas"]:
            t_id = taluka["taluka_id"]
            t_name = taluka["taluka_name"]
            
            # Format requested by user:
            # /home/downloads/dp/?cities=palghar&tal=dahanu&languages=
            # plus explicit language options english and marathi
            url_all = f"{BASE_URL}?cities={d_id}&tal={t_id}&languages="
            url_english = f"{BASE_URL}?cities={d_id}&tal={t_id}&languages=english"
            url_marathi = f"{BASE_URL}?cities={d_id}&tal={t_id}&languages=marathi"

            query_url_entry = {
                "district_id": d_id,
                "district_name": d_name,
                "taluka_id": t_id,
                "taluka_name": t_name,
                "urls": {
                    "all_languages": url_all,
                    "english": url_english,
                    "marathi": url_marathi
                }
            }
            all_urls.append(query_url_entry)
            total_query_urls += 3

            # Update individual taluka JSON file
            t_json_rel_path = taluka["json_file"]
            t_json_path = Path(t_json_rel_path)
            if t_json_path.exists():
                with open(t_json_path, "r", encoding="utf-8") as tf:
                    t_data = json.load(tf)

                t_data["query_urls"] = {
                    "default": url_all,
                    "english": url_english,
                    "marathi": url_marathi
                }

                # Ensure PDF storage folder structure exists for this taluka
                safe_t_id = re.sub(r'[\/\\:\*\?"<>\|]', '_', t_id)
                pdf_folder = Path(f"districts/{d_id}/pdfs/{safe_t_id}")
                pdf_folder.mkdir(parents=True, exist_ok=True)
                
                t_data["pdf_storage_dir"] = str(pdf_folder.as_posix())
                if "downloaded_pdfs" not in t_data:
                    t_data["downloaded_pdfs"] = []

                with open(t_json_path, "w", encoding="utf-8") as tf:
                    json.dump(t_data, tf, indent=2, ensure_ascii=False)

    # Save master URL list file
    master_urls_file = Path("data/all_query_urls.json")
    with open(master_urls_file, "w", encoding="utf-8") as f:
        json.dump(all_urls, f, indent=2, ensure_ascii=False)

    print(f"\nSuccessfully generated {total_query_urls} target query URLs!")
    print(f" Saved master URL list to: {master_urls_file}")
    print(f" Updated all individual taluka JSON files in 'districts/<district>/talukas/'")
    print(f" Created dedicated PDF download folders in 'districts/<district>/pdfs/<taluka>/'")

if __name__ == "__main__":
    generate_query_urls()
