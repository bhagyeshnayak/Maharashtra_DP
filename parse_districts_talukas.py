import json
import re
from pathlib import Path
from bs4 import BeautifulSoup

def extract_district_taluka_json():
    html_path = Path("metadata/dtp_page.html")
    if not html_path.exists():
        print("HTML file not found!")
        return

    html_content = html_path.read_text(encoding="utf-8")
    soup = BeautifulSoup(html_content, "html.parser")

    # 1. Extract District options from dropdown
    district_select = soup.find("select", {"id": "cities"})
    districts = []
    if district_select:
        for option in district_select.find_all("option"):
            val = option.get("value", "").strip()
            name = option.get_text(strip=True)
            if val and name != "Select District":
                districts.append({
                    "id": val,
                    "name": name
                })

    print(f"Extracted {len(districts)} districts from select dropdown.")

    # 2. Extract cityTalukaMap JS object from script tags
    js_map = {}
    pattern = r"const\s+cityTalukaMap\s*=\s*(\{[\s\S]*?\});"
    match = re.search(pattern, html_content)
    
    if match:
        js_str = match.group(1)
        # Clean JS string to be valid JSON (replace single quotes with double quotes)
        # Handle trailing commas or single quotes in keys/values
        # Parse manually or clean syntax
        try:
            # Simple JS object to JSON converter
            # Replace single quotes with double quotes where appropriate
            cleaned_js = js_str
            # Convert single-quoted string items like 'VASMATNAGAR' to "VASMATNAGAR"
            cleaned_js = re.sub(r"'([^'\\]*(?:\\.[^'\\]*)*)'", r'"\1"', cleaned_js)
            # Remove trailing commas before closing brackets/braces
            cleaned_js = re.sub(r",\s*([\]}])", r"\1", cleaned_js)
            js_map = json.loads(cleaned_js)
            print(f"Successfully parsed cityTalukaMap with {len(js_map)} district keys.")
        except Exception as e:
            print("Error parsing cityTalukaMap with json.loads, fallback to regex extraction:", e)
            # Fallback regex parser for JS object format
            current_key = None
            for line in js_str.splitlines():
                line = line.strip()
                key_match = re.search(r'"(\w+)":\s*\[', line)
                if key_match:
                    current_key = key_match.group(1)
                    if current_key not in js_map:
                        js_map[current_key] = []
                elif current_key:
                    # Extract string values
                    items = re.findall(r'["\']([^"\']+)["\']', line)
                    for item in items:
                        if item not in js_map[current_key]:
                            js_map[current_key].append(item)

    # 3. Combine into comprehensive structure
    combined_data = []
    
    # Helper for matching district keys
    def get_talukas_for_district(d_id, d_name):
        # Exact match
        if d_id in js_map:
            return js_map[d_id]
        # Case insensitive
        for k in js_map:
            if k.lower() == d_id.lower():
                return js_map[k]
        # Clean alphanumeric match (e.g. ahilyanagr vs ahilyanagar)
        clean_id = re.sub(r'[^a-z]', '', d_id.lower())
        clean_name = re.sub(r'[^a-z]', '', d_name.lower())
        for k in js_map:
            clean_k = re.sub(r'[^a-z]', '', k.lower())
            if clean_id.startswith(clean_k[:6]) or clean_k.startswith(clean_id[:6]) or clean_name.startswith(clean_k[:6]):
                return js_map[k]
        return []

    for d in districts:
        d_id = d["id"]
        d_name = d["name"]
        talukas = get_talukas_for_district(d_id, d_name)
        
        combined_data.append({
            "district_id": d_id,
            "district_name": d_name,
            "taluka_count": len(talukas),
            "talukas": [
                {
                    "taluka_name": t,
                    "taluka_id": re.sub(r'\s+', '_', t.lower())
                } for t in talukas
            ]
        })

    # Save to JSON files
    output_dir = Path("data")
    output_dir.mkdir(exist_ok=True)

    # File 1: Simple City-Taluka Map JSON
    with open(output_dir / "city_taluka_map.json", "w", encoding="utf-8") as f:
        json.dump(js_map, f, indent=2, ensure_ascii=False)

    # File 2: Full Detailed Districts & Talukas JSON
    with open(output_dir / "maharashtra_districts_and_talukas.json", "w", encoding="utf-8") as f:
        json.dump(combined_data, f, indent=2, ensure_ascii=False)

    # File 3: Summary JSON
    summary = {
        "source": "https://dtp.maharashtra.gov.in/home/downloads/dp/",
        "total_districts": len(districts),
        "total_talukas": sum(d["taluka_count"] for d in combined_data),
        "districts_summary": [
            {
                "district_id": d["district_id"],
                "district_name": d["district_name"],
                "taluka_count": d["taluka_count"]
            } for d in combined_data
        ]
    }
    with open(output_dir / "maharashtra_dp_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(f"\nSaved JSON files in '{output_dir.absolute()}':")
    print(" - city_taluka_map.json")
    print(" - maharashtra_districts_and_talukas.json")
    print(" - maharashtra_dp_summary.json")

if __name__ == "__main__":
    extract_district_taluka_json()
