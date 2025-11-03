# LinkVault API Project

### **Project 05**  
**Project Title**: LinkVault API – Bookmark & Tag Management System  
**Project Description**:  
Constructed a self-hosted bookmarking API that enables users to save, tag, and retrieve web links programmatically. The system supports duplicate detection, tag-based filtering, and CLI-based import/export in standard formats, functioning as a privacy-focused alternative to commercial bookmarking services.

**Objective**:  
- Design an API to store URLs with optional title, notes, and multiple tags  
- Implement duplicate URL detection using normalized URL hashing  
- Support filtering by tag, keyword, or archived status  
- Model `Bookmark` and `Tag` with a many-to-many relationship in SQLAlchemy  
- Create a CLI to export bookmarks in Netscape HTML format (standard for browsers)  
- Optionally auto-extract page titles using `requests` + `BeautifulSoup`  
- Return consistent, paginated JSON responses for large datasets  

**Tools Used**:  
- **Backend Framework**: Flask, Flask-SQLAlchemy, Flask-Migrate  
- **Web Scraping (optional)**: `requests`, `BeautifulSoup4`  
- **CLI**: Click for import/export operations  
- **Data Handling**: URL normalization (`urllib.parse`), hashing (`hashlib`)  
- **Database**: SQLite for simplicity and file-based persistence  

**Weeks (during training)**: 1-4 (both inclusive)  
**Project Type**: Lightweight data curation API focused on URL management, tagging, and interoperability  
**Outcome**:  
Delivered a functional, extensible bookmarking API with CLI interoperability and duplicate prevention. The system empowers users to own their link data and demonstrates practical Flask API development with real utility for developers and researchers.


# LinkVault CLI Client – `linkvault_client.py`

A **command-line interface (CLI)** client for interacting with the **LinkVault API** — a Flask-based bookmark and tag management system.
This tool allows you to **create, list, update, delete, export** bookmarks directly from the terminal, without needing a browser.

---

## Features

- **CRUD Operations** via REST API:
  - `create` – Add new bookmark
  - `list` – List bookmarks with filters (tags, search, archived, pagination)
  - `update` – Modify title, notes, tags 
  - `delete` – Remove bookmark
  - `toggle_archive` – Toggle archived state
- **Data Portability**:
  - `export` – Download all bookmarks in **Netscape HTML format** (compatible with Chrome, Firefox, Safari)
- **Flexible Tagging**:
  - Support for multiple tags via `--tag python --tag api` or `--tag "python,api"`
- **Paginated & Filterable Listing**

---

## Prerequisites

- Python 3.8+
- LinkVault API server running at `http://127.0.0.1:5000` (default)
- `requests` and `click` Python packages

---

## Installation

1. **Clone or download** the `linkvault_client.py` file.

2. **Install dependencies**:

```bash
pip install click requests
```

> No virtual environment required, but recommended.

---

## Setup

### 1. Start the LinkVault API Server

Ensure your Flask server is running:

```bash
python run.py
```

> Server must be active at `http://127.0.0.1:5000`

### 2. (Optional) Change Base URL

Edit the `BASE_URL` in the script if your server runs elsewhere:

```python
BASE_URL = "http://your-server:port"  # e.g., http://192.168.1.100:5000
```

---

## Usage

Run any command with:

```bash
python linkvault_client.py <command> [options]
```

Use `--help` for detailed help:

```bash
python linkvault_client.py --help
python linkvault_client.py create --help
```

---

## Commands

### Create a Bookmark

```bash
python linkvault_client.py create "https://github.com" \
  --title "GitHub" \
  --notes "Code hosting platform" \
  --tags python --tags git --tags dev
```

### List Bookmarks

```bash
# All bookmarks (paginated)
python linkvault_client.py list

# Filter by tag
python linkvault_client.py list --tag python --tag api

# Search keyword
python linkvault_client.py list --q flask

# Show archived only
python linkvault_client.py list --archived

# Pagination
python linkvault_client.py list --page 2 --per-page 20
```

### Update a Bookmark

```bash
python linkvault_client.py update 5 \
  --title "Updated Title" \
  --tags newtag --tags updated \
  --archived
```

### Delete a Bookmark

```bash
python linkvault_client.py delete 3
```

### Toggle Archive

```bash
python linkvault_client.py toggle_archive 7
```

### Export to Browser-Compatible HTML

```bash
python linkvault_client.py export my_bookmarks.html
```

> Open `my_bookmarks.html` in Chrome/Firefox → Import via Bookmarks Manager

---

## Example Workflow

```bash
# 1. Add a bookmark
python linkvault_client.py create "https://flask.palletsprojects.com" --tags flask --tags python

# 2. List with filter
python linkvault_client.py list --tag flask

# 3. Export all
python linkvault_client.py export vault_backup.html
```

---

## Project Structure (Recommended)

```
linkvault/
├── run.py                  # Flask server
├── linkvault.db            # SQLite database
├── linkvault_client.py     # This CLI client
└── bookmarks_export.html   # Exported file
```

---

## Notes

- **No direct DB access** – CLI talks to API only (secure & portable)
- Uses **Click** for elegant CLI parsing
- Uses **requests** for HTTP communication
- Supports **comma-separated tags**: `--tags "python,api,web"`
- All responses are printed in **pretty JSON**

---

## Team

**LinkVault API & CLI**  
Developed by:

- Shubham Kapolkar  
- Dhruv Malvankar  
- Kalpita Naik  
- Vrusha Naik

---

## License

MIT License – Free to use, modify, and distribute.

---

**LinkVault – Own Your Links. Organize with Tags. Export Anywhere.**

--- 

*For API documentation, see `bookmark_routes.py` or use Postman.*  
*For server CLI (direct DB access), see `linkvault` package.*