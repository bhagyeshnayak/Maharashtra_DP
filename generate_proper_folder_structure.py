import json
import os
import re
from pathlib import Path

def create_proper_folder_structure():
    # Load master JSON data
    master_file = Path("data/maharashtra_districts_and_talukas.json")
    if not master_file.exists():
        print("Master JSON file not found!")
        return

    with open(master_file, "r", encoding="utf-8") as f:
        districts = json.load(f)

    base_dir = Path("districts")
    base_dir.mkdir(exist_ok=True)

    master_index = []

    print(f"Creating proper folder structure in '{base_dir.absolute()}' for {len(districts)} districts...")

    for district in districts:
        d_id = district["district_id"]
        d_name = district["district_name"]
        
        # Folder for this district
        district_folder = base_dir / d_id
        district_folder.mkdir(exist_ok=True)
        
        # Subfolder for talukas
        talukas_folder = district_folder / "talukas"
        talukas_folder.mkdir(exist_ok=True)

        district_index_entry = {
            "district_id": d_id,
            "district_name": d_name,
            "taluka_count": district["taluka_count"],
            "district_file": f"districts/{d_id}/district.json",
            "talukas_dir": f"districts/{d_id}/talukas/",
            "talukas": []
        }

        # 1. Save district.json inside district folder
        district_json_data = {
            "district_id": d_id,
            "district_name": d_name,
            "total_talukas": district["taluka_count"],
            "source_url": f"https://dtp.maharashtra.gov.in/home/downloads/dp/?cities={d_id}",
            "talukas": district["talukas"]
        }

        with open(district_folder / "district.json", "w", encoding="utf-8") as f:
            json.dump(district_json_data, f, indent=2, ensure_ascii=False)

        # 2. Save individual JSON for each taluka
        for taluka in district["talukas"]:
            t_name = taluka["taluka_name"]
            t_id = taluka["taluka_id"]
            # Sanitize filename for OS path safety
            safe_filename = re.sub(r'[\/\\:\*\?"<>\|]', '_', t_id) + ".json"

            taluka_json_data = {
                "district_id": d_id,
                "district_name": d_name,
                "taluka_id": t_id,
                "taluka_name": t_name,
                "query_url": f"https://dtp.maharashtra.gov.in/home/downloads/dp/?cities={d_id}&tal={t_id}",
                "dp_plans": [] # Placeholder for fetched DP plan records
            }

            taluka_file_path = talukas_folder / safe_filename
            with open(taluka_file_path, "w", encoding="utf-8") as f:
                json.dump(taluka_json_data, f, indent=2, ensure_ascii=False)

            district_index_entry["talukas"].append({
                "taluka_id": t_id,
                "taluka_name": t_name,
                "json_file": f"districts/{d_id}/talukas/{safe_filename}"
            })

        master_index.append(district_index_entry)

    # Save root master index.json
    index_file = base_dir / "index.json"
    with open(index_file, "w", encoding="utf-8") as f:
        json.dump(master_index, f, indent=2, ensure_ascii=False)

    print(f"\nDone! Created proper folder structure:")
    print(f" Root Index: {index_file}")
    print(f" Total District Folders: {len(districts)}")
    print(f" Total Individual Taluka JSON Files: {sum(d['taluka_count'] for d in districts)}")

if __name__ == "__main__":
    create_proper_folder_structure()
