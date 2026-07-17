#!/usr/bin/env python3
"""
Docket Sync — Keep Notion Federal Docket database current.

Sources:
  - CourtListener API (automatic polling)
  - PACER text dumps, HTML reports, individual PDFs (manual add)

Usage:
  python docket_sync.py poll                          # Check CL for new entries
  python docket_sync.py add --file filing.txt         # Add from text/HTML/PDF
  python docket_sync.py add --file 44.pdf --docket-number 44 --date 2025-12-20
  python docket_sync.py sync                          # Full sync
  python docket_sync.py list                          # Show existing entries
"""

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# Load config
ENV_PATH = Path(__file__).parent / ".env"
load_dotenv(ENV_PATH)

CL_TOKEN = os.getenv("COURTLISTENER_TOKEN", "")
NOTION_TOKEN = os.getenv("NOTION_TOKEN", "")
NOTION_DB_ID = os.getenv("NOTION_DATABASE_ID", "cc882170f6f549d3bfc6c0e31b5152f2")
NOTION_DS_ID = os.getenv("NOTION_DATA_SOURCE_ID", "db10c282-831f-439e-ac4e-d0d7b201940a")
CL_DOCKET_ID = os.getenv("CL_DOCKET_ID", "71294630")

CL_BASE = "https://www.courtlistener.com"
NOTION_BASE = "https://api.notion.com/v1"

MAX_CHUNK_CHARS = 8000  # ~2000 tokens per code block


# ─── Document Classification ────────────────────────────────────────

DOC_TYPE_RULES = [
    ("Motion", ["motion to", "motion for", "moves this court"]),
    ("Order", ["order", "ordered", "it is ordered", "text order", "minute entry"]),
    ("Opposition", ["opposition", "response in opposition", "brief in opposition"]),
    ("Reply", ["reply"]),
    ("Notice", ["notice", "waiver of service"]),
    ("Pleading", ["complaint", "amended complaint"]),
    ("Transcript", ["transcript"]),
    ("Discovery", ["discovery", "subpoena", "compel"]),
]

FILED_BY_RULES = [
    ("Court", ["order", "text order", "minute entry", "standing order",
               "assigned to", "it is ordered"]),
    ("Defense", ["defendant", "block & associates", "beverly a. block",
                 "george c. thompson", "julianne c. beil",
                 "counsel for defendant"]),
]


def classify_doc_type(text: str) -> str:
    lower = text.lower()
    for dtype, keywords in DOC_TYPE_RULES:
        if any(kw in lower for kw in keywords):
            return dtype
    return "Other"


def classify_filed_by(text: str) -> str:
    lower = text.lower()
    for party, keywords in FILED_BY_RULES:
        if any(kw in lower for kw in keywords):
            return party
    return "Plaintiff"


# ─── Text Chunking ──────────────────────────────────────────────────

def chunk_text(text: str, max_chars: int = MAX_CHUNK_CHARS) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    chunks, current = [], ""
    for para in re.split(r"\n{2,}", text):
        if len(current) + len(para) + 2 > max_chars and current:
            chunks.append(current.strip())
            current = para
        else:
            current += "\n\n" + para if current else para
    if current.strip():
        chunks.append(current.strip())
    # Split any remaining oversized chunks on single newlines
    final = []
    for chunk in chunks:
        if len(chunk) <= max_chars:
            final.append(chunk)
        else:
            sub = ""
            for line in chunk.split("\n"):
                if len(sub) + len(line) + 1 > max_chars and sub:
                    final.append(sub.strip())
                    sub = line
                else:
                    sub += "\n" + line if sub else line
            if sub.strip():
                final.append(sub.strip())
    return final


def build_page_content(sections: list[dict]) -> str:
    """Build Notion markdown content from sections with code blocks."""
    parts = []
    for section in sections:
        parts.append(f"## {section['label']}")
        for chunk in section["chunks"]:
            parts.append(f"```\n{chunk}\n```")
    return "\n\n".join(parts)


# ─── CourtListener Source ────────────────────────────────────────────

def courtlistener_poll(existing_numbers: set[str]) -> list[dict]:
    """Fetch docket entries from CourtListener, return new ones."""
    if not CL_TOKEN:
        print("ERROR: COURTLISTENER_TOKEN not set in .env")
        return []

    headers = {"Authorization": f"Token {CL_TOKEN}"}
    url = f"{CL_BASE}/api/rest/v4/docket-entries/"
    params = {
        "docket": CL_DOCKET_ID,
        "order_by": "-date_filed",
        "page_size": 100,
    }

    print(f"Polling CourtListener for docket {CL_DOCKET_ID}...")
    resp = requests.get(url, headers=headers, params=params)
    if resp.status_code == 401:
        print("ERROR: CourtListener auth failed. Check your token.")
        print("Note: Docket entry access may require contacting CL for approval.")
        return []
    if resp.status_code == 403:
        print("ERROR: Access denied. You may need to contact CourtListener")
        print("       to request docket entry API access.")
        return []
    resp.raise_for_status()

    data = resp.json()
    entries = data.get("results", [])
    print(f"Found {len(entries)} total entries on CourtListener")

    new_entries = []
    for entry in entries:
        num = str(entry.get("entry_number", ""))
        if num in existing_numbers:
            continue

        # Build CourtListener URL
        cl_url = f"{CL_BASE}/docket/{CL_DOCKET_ID}/{num}/mullins-v-duquesne-university-of-the-holy-spirit/"

        # Get plain text from recap documents if available
        full_text = ""
        for doc in entry.get("recap_documents", []):
            txt = doc.get("plain_text", "")
            if txt:
                full_text += txt + "\n\n"

        description = entry.get("description", f"Docket Entry {num}")
        date_filed = entry.get("date_filed", "")

        new_entries.append({
            "docket_number": num,
            "name": description[:120],
            "filing_date": date_filed,
            "full_text": full_text.strip(),
            "courtlistener_url": cl_url,
            "doc_type": classify_doc_type(description),
            "filed_by": classify_filed_by(description + " " + full_text[:500]),
        })

    print(f"New entries not in Notion: {len(new_entries)}")
    return new_entries


# ─── PACER Text Dump Source ──────────────────────────────────────────

def parse_pacer_text(filepath: str) -> list[dict]:
    """Parse a PACER text dump (like docket_output.txt) into entries."""
    with open(filepath, "r", encoding="utf-8") as f:
        text = f.read()

    # Split on ---PAGE N--- markers
    parts = re.split(r"---PAGE (\d+)---", text)
    if len(parts) < 3:
        # No page markers — treat as single document
        print("No ---PAGE N--- markers found. Treating as single document.")
        return [{
            "docket_number": "0",
            "name": Path(filepath).stem,
            "filing_date": "",
            "full_text": text.strip(),
            "courtlistener_url": "",
            "doc_type": classify_doc_type(text[:500]),
            "filed_by": classify_filed_by(text[:500]),
        }]

    page_contents = {}
    for i in range(1, len(parts), 2):
        page_contents[int(parts[i])] = parts[i + 1]

    # Parse headers
    header_re = re.compile(
        r"Case 2:25-cv-01366-MJH\s*:?\s*Document\s+(\S+)\s+Filed\s+(\S+)\s+Page\s+(\d+)\s+of\s+(\d+)"
    )

    subdocs = defaultdict(list)
    last_doc = "1"
    last_filed = ""
    for pn in sorted(page_contents.keys()):
        content = page_contents[pn]
        m = header_re.search(content)
        if m:
            doc_num, filed, page_num, total = m.group(1), m.group(2), m.group(3), m.group(4)
            last_doc = doc_num
            last_filed = filed
        else:
            doc_num = last_doc
            filed = last_filed
        # Clean header from content
        cleaned = header_re.sub("", content).strip()
        subdocs[doc_num].append({"text": cleaned, "filed": filed})

    # Group by parent document
    parents = defaultdict(list)
    for doc_num in subdocs:
        parent = doc_num.split("-")[0]
        parents[parent].append(doc_num)

    entries = []
    for parent_num in sorted(parents.keys(), key=lambda x: int(x) if x.isdigit() else 999):
        child_docs = sorted(parents[parent_num], key=lambda x: (len(x), x))

        # Combine text from all child documents
        sections = []
        filing_date = ""
        for doc_num in child_docs:
            pages = subdocs[doc_num]
            if pages and pages[0]["filed"]:
                filing_date = pages[0]["filed"]
            combined = "\n\n".join(p["text"] for p in pages).strip()
            total_pages = len(pages)
            chunks = chunk_text(combined)
            sections.append({
                "label": f"Document {doc_num} ({total_pages} pages)",
                "chunks": chunks,
            })

        # Parse date
        iso_date = ""
        if filing_date:
            try:
                iso_date = datetime.strptime(filing_date, "%m/%d/%y").strftime("%Y-%m-%d")
            except ValueError:
                iso_date = filing_date

        # Extract name from first section text
        all_text = sections[0]["chunks"][0] if sections and sections[0]["chunks"] else ""
        name = extract_doc_name(all_text)

        entries.append({
            "docket_number": parent_num,
            "name": name,
            "filing_date": iso_date,
            "full_text": all_text,
            "sections": sections,
            "courtlistener_url": f"{CL_BASE}/docket/{CL_DOCKET_ID}/{parent_num}/mullins-v-duquesne-university-of-the-holy-spirit/",
            "doc_type": classify_doc_type(name + " " + all_text[:300]),
            "filed_by": classify_filed_by(name + " " + all_text[:500]),
        })

    print(f"Parsed {len(entries)} entries from text dump")
    return entries


def extract_doc_name(text: str) -> str:
    """Extract document title from first page of text."""
    skip_patterns = [
        r"^IN THE UNITED STATES", r"^FOR THE WESTERN DISTRICT",
        r"^DAVID\s*(MICHAEL)?\s*MULLINS", r"^Plaintiff", r"^Defendant",
        r"^v\.", r"^DUQUESNE", r"^Civil", r"^2:25", r"^\)", r"^\d+$",
        r"^ALICIA SIMPSON", r"^ADAM WASILKO", r"^ANNE MULLARKEY",
        r"^DANIEL SELCER", r"^HOLY SPIRIT", r"^Defendants?\.$",
    ]
    skip_res = [re.compile(p, re.IGNORECASE) for p in skip_patterns]
    doc_keywords = [
        "MOTION", "ORDER", "OPINION", "NOTICE", "COMPLAINT", "MEMORANDUM",
        "BRIEF", "RESPONSE", "REPLY", "HEARING", "WAIVER", "EXHIBIT",
        "APPLICATION", "PETITION", "ANSWER",
    ]

    for line in text.split("\n")[:40]:
        line = line.strip()
        if len(line) < 5:
            continue
        if any(r.search(line) for r in skip_res):
            continue
        for kw in doc_keywords:
            if kw.lower() in line.lower():
                return line[:120]
        if len(line) > 15:
            return line[:120]
    return "Untitled Filing"


# ─── PACER HTML Source ───────────────────────────────────────────────

def parse_pacer_html(filepath: str) -> list[dict]:
    """Parse a PACER HTML docket report into entries."""
    with open(filepath, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    entries = []
    # PACER docket reports use a table with class "docket_entry" or similar
    # The structure varies but typically has rows with: date, #, description
    rows = soup.select("table tr") or soup.find_all("tr")

    for row in rows:
        cells = row.find_all("td")
        if len(cells) < 3:
            continue

        # Try to extract: date, docket number, description
        date_text = cells[0].get_text(strip=True)
        num_text = cells[1].get_text(strip=True)
        desc_text = cells[2].get_text(strip=True) if len(cells) > 2 else ""

        # Validate date format (MM/DD/YYYY or MM/DD/YY)
        date_match = re.match(r"(\d{1,2}/\d{1,2}/\d{2,4})", date_text)
        if not date_match:
            continue

        # Validate docket number
        num_match = re.match(r"(\d+)", num_text)
        if not num_match:
            continue

        filing_date = date_match.group(1)
        try:
            if len(filing_date.split("/")[-1]) == 2:
                iso_date = datetime.strptime(filing_date, "%m/%d/%y").strftime("%Y-%m-%d")
            else:
                iso_date = datetime.strptime(filing_date, "%m/%d/%Y").strftime("%Y-%m-%d")
        except ValueError:
            iso_date = ""

        docket_num = num_match.group(1)

        entries.append({
            "docket_number": docket_num,
            "name": desc_text[:120] or f"Docket Entry {docket_num}",
            "filing_date": iso_date,
            "full_text": desc_text,
            "courtlistener_url": "",
            "doc_type": classify_doc_type(desc_text),
            "filed_by": classify_filed_by(desc_text),
        })

    print(f"Parsed {len(entries)} entries from HTML report")
    return entries


# ─── PDF Source ──────────────────────────────────────────────────────

def parse_ecf_pdf(filepath: str, docket_number: str = "",
                   filing_date: str = "") -> list[dict]:
    """Extract text from an ECF PDF filing."""
    try:
        import fitz  # pymupdf
    except ImportError:
        print("ERROR: pymupdf not installed. Run: pip install pymupdf")
        return []

    doc = fitz.open(filepath)
    full_text = ""
    for page in doc:
        full_text += page.get_text() + "\n\n"
    doc.close()
    full_text = full_text.strip()

    if not docket_number:
        # Try to extract from filename (e.g., "44.pdf" or "ecf_44.pdf")
        stem = Path(filepath).stem
        m = re.search(r"(\d+)", stem)
        docket_number = m.group(1) if m else "0"

    if not filing_date:
        # Try to extract from document text
        m = re.search(r"Filed\s+(\d{1,2}/\d{1,2}/\d{2,4})", full_text)
        if m:
            try:
                d = m.group(1)
                if len(d.split("/")[-1]) == 2:
                    filing_date = datetime.strptime(d, "%m/%d/%y").strftime("%Y-%m-%d")
                else:
                    filing_date = datetime.strptime(d, "%m/%d/%Y").strftime("%Y-%m-%d")
            except ValueError:
                pass

    name = extract_doc_name(full_text)
    chunks = chunk_text(full_text)

    return [{
        "docket_number": docket_number,
        "name": name,
        "filing_date": filing_date,
        "full_text": full_text,
        "sections": [{"label": f"Document {docket_number} ({len(chunks)} chunks)", "chunks": chunks}],
        "courtlistener_url": f"{CL_BASE}/docket/{CL_DOCKET_ID}/{docket_number}/mullins-v-duquesne-university-of-the-holy-spirit/" if docket_number != "0" else "",
        "doc_type": classify_doc_type(name + " " + full_text[:300]),
        "filed_by": classify_filed_by(name + " " + full_text[:500]),
    }]


# ─── Notion Integration ─────────────────────────────────────────────

def notion_headers():
    return {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28",
    }


def get_existing_docket_numbers() -> dict[str, str]:
    """Query Notion database for existing docket numbers. Returns {number: page_id}."""
    if not NOTION_TOKEN:
        print("WARNING: NOTION_TOKEN not set. Cannot check for duplicates.")
        return {}

    url = f"{NOTION_BASE}/databases/{NOTION_DB_ID}/query"
    existing = {}
    start_cursor = None

    while True:
        body = {"page_size": 100}
        if start_cursor:
            body["start_cursor"] = start_cursor

        resp = requests.post(url, headers=notion_headers(), json=body)
        if resp.status_code != 200:
            print(f"WARNING: Notion query failed ({resp.status_code}). Skipping dedup.")
            return {}

        data = resp.json()
        for page in data.get("results", []):
            props = page.get("properties", {})
            dn_prop = props.get("Docket Number", {})
            # Rich text property
            rich_text = dn_prop.get("rich_text", [])
            if rich_text:
                num = rich_text[0].get("plain_text", "")
                if num:
                    existing[num] = page["id"]

        if not data.get("has_more"):
            break
        start_cursor = data.get("next_cursor")

    return existing


def create_notion_page(entry: dict, dry_run: bool = False) -> bool:
    """Create a new page in the Notion Federal Docket database."""
    # Build content with code blocks
    if "sections" in entry and entry["sections"]:
        content = build_page_content(entry["sections"])
    elif entry.get("full_text"):
        chunks = chunk_text(entry["full_text"])
        content = build_page_content([{
            "label": f"Document {entry['docket_number']}",
            "chunks": chunks,
        }])
    else:
        content = ""

    page_data = {
        "docket_number": entry["docket_number"],
        "name": entry["name"],
        "filing_date": entry["filing_date"],
        "doc_type": entry.get("doc_type", ""),
        "filed_by": entry.get("filed_by", ""),
        "courtlistener_url": entry.get("courtlistener_url", ""),
        "content_length": len(content),
    }

    if dry_run:
        print(f"  [DRY RUN] Would create: Doc {entry['docket_number']}: {entry['name'][:60]}")
        print(f"    Date: {entry['filing_date']}, Type: {entry.get('doc_type')}, By: {entry.get('filed_by')}")
        print(f"    Content: {len(content):,} chars")
        return True

    if not NOTION_TOKEN:
        # Output as JSON for Claude Code MCP tools
        output = {
            "properties": {
                "Name": entry["name"],
                "Docket Number": entry["docket_number"],
                "date:Filing Date:start": entry["filing_date"],
                "Document Type": entry.get("doc_type", ""),
                "Filed By": entry.get("filed_by", ""),
                "CourtListener URL": entry.get("courtlistener_url", ""),
            },
            "content": content,
        }
        outfile = Path(__file__).parent / f"pending_doc_{entry['docket_number']}.json"
        with open(outfile, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        print(f"  Saved to {outfile} (no Notion token — use Claude Code MCP to create)")
        return True

    # Create via Notion API
    properties = {
        "Name": {"title": [{"text": {"content": entry["name"]}}]},
        "Docket Number": {"rich_text": [{"text": {"content": entry["docket_number"]}}]},
        "Document Type": {"select": {"name": entry.get("doc_type", "Other")}},
        "Filed By": {"select": {"name": entry.get("filed_by", "Plaintiff")}},
    }
    if entry.get("filing_date"):
        properties["Filing Date"] = {"date": {"start": entry["filing_date"]}}
    if entry.get("courtlistener_url"):
        properties["CourtListener URL"] = {"url": entry["courtlistener_url"]}

    body = {
        "parent": {"database_id": NOTION_DB_ID},
        "properties": properties,
    }

    # Create the page
    resp = requests.post(f"{NOTION_BASE}/pages", headers=notion_headers(), json=body)
    if resp.status_code != 200:
        print(f"  ERROR creating page: {resp.status_code} {resp.text[:200]}")
        return False

    page_id = resp.json()["id"]
    print(f"  Created page {page_id}")

    # Add content as child blocks (code blocks)
    if content:
        add_content_blocks(page_id, content)

    return True


def add_content_blocks(page_id: str, content: str):
    """Add code block content to a Notion page."""
    # Split content into code blocks
    blocks = []
    for match in re.finditer(r"## (.+?)(?=\n|$)", content):
        blocks.append({
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"text": {"content": match.group(1)}}]
            }
        })

    for match in re.finditer(r"```\n(.*?)```", content, re.DOTALL):
        code_text = match.group(1).strip()
        # Notion code block content limit is 2000 chars
        if len(code_text) > 2000:
            # Split into multiple code blocks
            for i in range(0, len(code_text), 2000):
                chunk = code_text[i:i+2000]
                blocks.append({
                    "object": "block",
                    "type": "code",
                    "code": {
                        "rich_text": [{"text": {"content": chunk}}],
                        "language": "plain text",
                    }
                })
        else:
            blocks.append({
                "object": "block",
                "type": "code",
                "code": {
                    "rich_text": [{"text": {"content": code_text}}],
                    "language": "plain text",
                }
            })

    # Append blocks in batches of 100
    url = f"{NOTION_BASE}/blocks/{page_id}/children"
    for i in range(0, len(blocks), 100):
        batch = blocks[i:i+100]
        resp = requests.patch(url, headers=notion_headers(),
                              json={"children": batch})
        if resp.status_code != 200:
            print(f"  WARNING: Block append failed: {resp.status_code}")


# ─── CLI Commands ────────────────────────────────────────────────────

def cmd_poll(args):
    """Poll CourtListener for new entries."""
    existing = get_existing_docket_numbers()
    print(f"Existing entries in Notion: {len(existing)}")

    new_entries = courtlistener_poll(set(existing.keys()))
    if not new_entries:
        print("No new entries found.")
        return

    for entry in sorted(new_entries, key=lambda e: int(e["docket_number"]) if e["docket_number"].isdigit() else 999):
        print(f"\nNew: Doc {entry['docket_number']}: {entry['name'][:60]}")
        print(f"  Filed: {entry['filing_date']}, Type: {entry['doc_type']}, By: {entry['filed_by']}")
        if not args.dry_run:
            create_notion_page(entry)
        else:
            create_notion_page(entry, dry_run=True)


def cmd_add(args):
    """Add entries from a file."""
    filepath = args.file
    if not os.path.exists(filepath):
        print(f"ERROR: File not found: {filepath}")
        return

    ext = Path(filepath).suffix.lower()

    if ext == ".pdf":
        entries = parse_ecf_pdf(filepath, args.docket_number or "", args.date or "")
    elif ext in (".html", ".htm"):
        entries = parse_pacer_html(filepath)
    else:
        entries = parse_pacer_text(filepath)

    if not entries:
        print("No entries parsed from file.")
        return

    # Dedup
    existing = get_existing_docket_numbers()
    print(f"Existing entries in Notion: {len(existing)}")

    created, skipped = 0, 0
    for entry in entries:
        dn = entry["docket_number"]
        if dn in existing and not args.force:
            skipped += 1
            continue

        print(f"\nAdding: Doc {dn}: {entry['name'][:60]}")
        if not args.dry_run:
            if create_notion_page(entry):
                created += 1
        else:
            create_notion_page(entry, dry_run=True)
            created += 1

    print(f"\nDone: {created} created, {skipped} skipped (already exist)")


def cmd_sync(args):
    """Full sync: poll CL + reconcile."""
    print("=== Full Sync ===\n")
    print("Step 1: Polling CourtListener...")
    cmd_poll(args)
    print("\nSync complete.")


def cmd_list(args):
    """List existing entries."""
    existing = get_existing_docket_numbers()
    print(f"Existing entries in Notion ({len(existing)}):")
    for num in sorted(existing.keys(), key=lambda x: int(x) if x.isdigit() else 999):
        print(f"  Doc {num}: {existing[num]}")


def main():
    parser = argparse.ArgumentParser(description="Docket Sync — Federal Docket to Notion")
    parser.add_argument("--dry-run", action="store_true", help="Preview without creating pages")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("poll", help="Poll CourtListener for new entries")
    sub.add_parser("sync", help="Full sync (poll CL + reconcile)")
    sub.add_parser("list", help="List existing Notion entries")

    add_parser = sub.add_parser("add", help="Add from file (text/HTML/PDF)")
    add_parser.add_argument("--file", required=True, help="Path to filing file")
    add_parser.add_argument("--docket-number", help="Override docket number (for PDFs)")
    add_parser.add_argument("--date", help="Override filing date (YYYY-MM-DD)")
    add_parser.add_argument("--force", action="store_true", help="Overwrite existing entries")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    {"poll": cmd_poll, "add": cmd_add, "sync": cmd_sync, "list": cmd_list}[args.command](args)


if __name__ == "__main__":
    main()
