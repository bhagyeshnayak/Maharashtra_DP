# Maharashtra DP - District & Taluka Development Plan Downloader

Automated crawler, metadata parser, and structured JSON folder generator for all 34 Districts and 307 Talukas/Towns from the Directorate of Town Planning and Valuation, Maharashtra State ([dtp.maharashtra.gov.in](https://dtp.maharashtra.gov.in/home/downloads/dp/)).

---

## 📁 Repository & Storage Structure

```text
Maharashtra_DP/
│
├── districts/                                     # Master District & Taluka PDF storage
│   ├── index.json                                 # Master directory index
│   ├── palghar/                                   # District Folders
│   ├── pune/
│   └── ... (34 Districts with individual Taluka JSONs & PDF folders)
│
├── data/                                          # Consolidated JSON Datasets
│   ├── maharashtra_districts_and_talukas.json
│   ├── city_taluka_map.json
│   └── all_query_urls.json
│
├── download_all_district_taluka_pdfs.py           # Main multi-threaded PDF Downloader
├── parse_districts_talukas.py                     # District/Taluka metadata parser
├── generate_proper_folder_structure.py           # Folder hierarchy generator
├── generate_all_query_urls.py                     # Query URL generator
├── check_download_progress.py                     # Progress checker script
└── monitor_live.py                                # Real-time live status monitor
```

---

## 🚀 How to Run

### 1. Download All PDFs (Multi-threaded Downloader)
To start or resume downloading Development Plan PDFs across all 307 Talukas:
```bash
python download_all_district_taluka_pdfs.py
```

### 2. Real-Time Download Monitor
To view live download counters:
```bash
python monitor_live.py
```

### 3. Check Progress Report
To check total downloaded PDFs and disk size:
```bash
python check_download_progress.py
```

---

## 🔗 District & Taluka Dataset Summary
- **Total Districts**: `34`
- **Total Talukas / Towns**: `307`
- **Generated Target Query URLs**: `921`
- **Source Portal**: [Directorate of Town Planning Maharashtra](https://dtp.maharashtra.gov.in/home/downloads/dp/)
