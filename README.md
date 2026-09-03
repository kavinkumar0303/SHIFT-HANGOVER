# SHIFT//HANDOVER 📋⚡
### Automated Shift Handover Intelligence, Deduplication & Database Persistence Engine

A deterministic, production-grade Shift Handover Note Generator featuring an integrated SQLite database layer, resilient ingestion pipeline, CLI trigger, web dashboard, and Flutter frontend UI with an **"Obsidian + Electric Mint"** enterprise NOC visual system.

---

## 🗄️ Database Architecture (SQLite)

- **Database Engine**: Built-in Python `sqlite3`
- **Database File**: `database/shift_handover.db`
- **Database Module**: [`database.py`](file:///Users/kavinxyz/Downloads/shift%20hangover/database.py)

### 📊 Database Schema & Tables

#### 1. `tickets`
Stores ticketing activity records (Jira, ServiceNow) with unique constraint on `record_id`.
```sql
CREATE TABLE tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    record_id TEXT UNIQUE NOT NULL,
    summary TEXT NOT NULL,
    status TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    source TEXT DEFAULT 'Ticketing',
    priority TEXT,
    description TEXT,
    created_at TEXT
);
```

#### 2. `incidents`
Stores production incident records (PagerDuty, CloudWatch alerts) with unique constraint on `record_id`.
```sql
CREATE TABLE incidents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    record_id TEXT UNIQUE NOT NULL,
    summary TEXT NOT NULL,
    status TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    source TEXT DEFAULT 'Incident',
    severity TEXT,
    description TEXT,
    created_at TEXT
);
```

#### 3. `handover_reports`
Stores metadata and KPI metrics for each generated shift handover note.
```sql
CREATE TABLE handover_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    shift_start TEXT NOT NULL,
    shift_end TEXT NOT NULL,
    generated_at TEXT NOT NULL,
    total_items INTEGER DEFAULT 0,
    completed_count INTEGER DEFAULT 0,
    in_progress_count INTEGER DEFAULT 0,
    blockers_count INTEGER DEFAULT 0,
    watchlist_count INTEGER DEFAULT 0,
    pdf_filename TEXT,
    pdf_path TEXT
);
```

#### 4. `handover_items`
Stores every classified handover line item linked to its parent report.
```sql
CREATE TABLE handover_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id INTEGER NOT NULL,
    section TEXT NOT NULL,
    summary TEXT NOT NULL,
    source TEXT NOT NULL,
    record_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    FOREIGN KEY (report_id) REFERENCES handover_reports(id) ON DELETE CASCADE
);
```

---

## 🔄 End-to-End Pipeline & Data Flow

```
JSON Seed Feeds (data/tickets.json, data/incidents.json)
      ↓ (Idempotent UPSERT on record_id)
    SQLite (database/shift_handover.db)
      ↓
fetch_activity.py (Database Ingestion & Resilience)
      ↓
Shift Window Filter (Half-open interval: [shift_start, shift_end))
      ↓
Normalization (Timezone parsing & UTC alignment)
      ↓
Deduplication & Collapsing (Group by (source, record_id) -> Chronological progression trail)
      ↓
Generator (Deterministic rule classification into 4 sections)
      ↓
Handover Sections (COMPLETED, IN PROGRESS, BLOCKERS / ESCALATIONS, WATCH-LIST)
      ↓
SQLite Report History (Saved to handover_reports & handover_items)
      ↓
PDF Publisher (ReportLab executive-grade single PDF with "Nothing to report.")
      ↓
Web Dashboard / Flutter UI / CLI
```

---

## 🚀 Getting Started

### 1. Initialize SQLite Database
```bash
# Creates database/shift_handover.db, builds tables, and seeds initial data idempotently
python3 database.py
```
*Output:*
```
Database initialized successfully.
Database: database/shift_handover.db
Tickets: 13
Incidents: 10
Reports: 0
```

### 2. Start the Backend API & Web Application
```bash
# Launch Flask backend on port 5050
python3 app.py
```
Open **[http://localhost:5050](http://localhost:5050)** in your browser.

### 3. Run the CLI Generator
```bash
python3 generate_note.py \
  --shift-start "2026-09-03T17:00:00+05:30" \
  --shift-end "2026-09-03T20:00:00+05:30" \
  --output "output/handover_note.pdf"
```

---

## 📡 REST API Endpoints

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| **`/api/status`** | `GET` | Returns database health, ticket/incident/report counts, and feed connections. |
| **`/api/generate`** | `POST` | Ingests from SQLite, filters shift window, deduplicates, classifies into 4 sections, generates PDF, and stores report in SQLite. |
| **`/api/reports`** | `GET` | Returns list of all previous handover reports from SQLite database. |
| **`/api/reports/<id>`** | `GET` | Returns full classified sections and items for a specific handover report. |
| **`/api/data/tickets`** | `GET` | Returns all tickets stored in SQLite. |
| **`/api/data/incidents`** | `GET` | Returns all incidents stored in SQLite. |
| **`/api/download/<filename>`** | `GET` | Serves binary PDF with `Content-Type: application/pdf` and `Content-Disposition: inline` (preview) or `attachment` (`?download=1`). |
| **`/api/login`** | `POST` | Authenticates operator with credentials and issues session profile. |
| **`/api/me`** | `GET` | Returns active operator profile. |

---

## 🧪 Automated Testing

Run the full pytest suite (20 unit and integration tests):
```bash
pytest test_pipeline.py -v
```
*Result: 20 passed in 0.32s (100% pass rate)*
