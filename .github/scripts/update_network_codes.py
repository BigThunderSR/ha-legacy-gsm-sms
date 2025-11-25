#!/usr/bin/env python3
"""Update network operator codes from public sources."""

import json
import re
import sys
from datetime import datetime
from email.utils import parsedate_to_datetime
from pathlib import Path

import requests

# Public data sources - multiple fallback options
# Each source will be checked for availability and last update time
# Only includes verified, currently available sources
SOURCES = [
    # Primary GitHub sources
    {
        "name": "musalbas/mcc-mnc-table",
        "url": "https://raw.githubusercontent.com/musalbas/mcc-mnc-table/master/mcc-mnc-table.json",
        "repo": "musalbas/mcc-mnc-table",
        "file": "mcc-mnc-table.json",
        "format": "list",  # List of objects
    },
    {
        "name": "pbakondy/mcc-mnc-list",
        "url": "https://raw.githubusercontent.com/pbakondy/mcc-mnc-list/master/mcc-mnc-list.json",
        "repo": "pbakondy/mcc-mnc-list",
        "file": "mcc-mnc-list.json",
        "format": "list",  # List of objects
    },
    # CDN mirrors (provide redundancy if GitHub is unavailable)
    {
        "name": "jsdelivr CDN (mcc-mnc-list mirror)",
        "url": "https://cdn.jsdelivr.net/npm/mcc-mnc-list@latest/mcc-mnc-list.json",
        "repo": None,  # CDN, no GitHub repo
        "file": None,
        "format": "list",  # List of objects
    },
    {
        "name": "unpkg CDN (mcc-mnc-list mirror)",
        "url": "https://unpkg.com/mcc-mnc-list/mcc-mnc-list.json",
        "repo": None,  # CDN, no GitHub repo
        "file": None,
        "format": "list",  # List of objects
    },
]


def get_source_last_update(source, response):
    """Get the last update time for a source.
    
    First tries the Last-Modified header from the raw file response,
    then falls back to GitHub API if needed.
    
    Args:
        source: Dictionary containing 'repo' and 'file' keys for GitHub API lookup
        response: requests.Response object from fetching the raw file
    
    Returns:
        datetime object representing last update time, or None if unavailable
    """
    # Try to get Last-Modified header from the response
    last_modified = response.headers.get('Last-Modified')
    if last_modified:
        try:
            # Parse HTTP date format (RFC 2822)
            return parsedate_to_datetime(last_modified)
        except (ValueError, TypeError):
            pass
    
    # Fallback: Try GitHub API (may hit rate limits, only for GitHub sources)
    if source.get('repo') and source.get('file'):
        try:
            url = f"https://api.github.com/repos/{source['repo']}/commits"
            params = {"path": source["file"], "per_page": 1}
            
            api_response = requests.get(url, params=params, timeout=10)
            if api_response.status_code == 200:
                commits = api_response.json()
                if commits:
                    commit_date_str = commits[0]["commit"]["committer"]["date"]
                    # Parse ISO 8601 date
                    commit_date = datetime.fromisoformat(commit_date_str.replace('Z', '+00:00'))
                    return commit_date
        except (requests.exceptions.RequestException, ValueError, KeyError, IndexError):
            pass
    
    return None


def fetch_from_source(source):
    """Fetch MCC-MNC data from a specific source.
    
    Args:
        source: Dictionary containing 'name', 'url', 'repo', and 'file' keys
    
    Returns:
        Tuple of (data, last_update) where data is the JSON response or None,
        and last_update is a datetime object or None
    """
    try:
        print(f"  Trying source: {source['name']}")
        print(f"    URL: {source['url']}")
        
        response = requests.get(source["url"], timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        # Validate that we got data
        if not data:
            print(f"    Warning: Source returned empty data")
            return None, None
        
        entry_count = len(data) if isinstance(data, (list, dict)) else 0
        print(f"    ✓ Success: Retrieved {entry_count} entries")
        
        # Get last update time for this source (pass the response for headers)
        last_update = get_source_last_update(source, response)
        if last_update:
            print(f"    Last updated: {last_update.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        else:
            print(f"    Last updated: Unable to determine")
        
        return data, last_update
        
    except requests.exceptions.HTTPError as e:
        status = e.response.status_code if e.response is not None else "Unknown"
        print(f"    ✗ HTTP Error {status}: {e}")
        return None, None
    except (requests.exceptions.RequestException, json.JSONDecodeError, ValueError, KeyError) as e:
        print(f"    ✗ Failed: {e}")
        return None, None


def parse_data_to_codes(data, source_format):
    """Parse data from various source formats into our standard format.
    
    Args:
        data: Raw JSON data from the source (list or dict)
        source_format: Format type, currently supports "list"
    
    Returns:
        Dictionary mapping MCCMNC codes to operator names
    """
    codes = {}
    
    if not data:
        return codes
    
    if source_format == "list":
        # Handle list-based formats (most sources)
        for entry in data:
            # Get values, ensuring they're not None
            mcc = entry.get('mcc')
            mnc = entry.get('mnc')
            
            # Skip if mcc or mnc is None or not convertible to string
            if mcc is None or mnc is None:
                continue
            
            # Convert to string
            mcc = str(mcc).strip()
            mnc = str(mnc).strip()
            
            # Try different field names for operator name
            operator = (entry.get('network') or 
                       entry.get('brand') or 
                       entry.get('operator') or '')
            
            # Ensure we have valid numeric MCC/MNC and operator name
            if mcc and mnc and operator and mcc.isdigit() and mnc.isdigit():
                # Pad MNC to 2-3 digits as needed
                code = f"{mcc}{mnc.zfill(2)}"
                codes[code] = operator
    
    return codes


def fetch_mcc_mnc_data():
    """Fetch MCC-MNC data from the most recently updated available source.
    
    Returns:
        Dictionary mapping MCCMNC codes to operator names, or empty dict if no sources available
    """
    print("\nChecking all available sources...")
    print("="*70)
    
    available_sources = []
    
    # Try each source and collect successful ones
    for source in SOURCES:
        data, last_update = fetch_from_source(source)
        
        if data:
            parsed_codes = parse_data_to_codes(data, source["format"])
            if parsed_codes:
                available_sources.append({
                    "source": source,
                    "data": parsed_codes,
                    "last_update": last_update,
                    "count": len(parsed_codes)
                })
    
    print("="*70)
    
    if not available_sources:
        print("\n✗ ERROR: No sources were available!")
        return {}
    
    # Separate sources with known update times from those without
    sources_with_dates = [s for s in available_sources if s["last_update"]]
    sources_without_dates = [s for s in available_sources if not s["last_update"]]
    
    # Sort sources with dates by most recent first, then by count
    sources_with_dates.sort(
        key=lambda x: (x["last_update"], x["count"]),
        reverse=True
    )
    
    # Sort sources without dates by count only
    sources_without_dates.sort(key=lambda x: x["count"], reverse=True)
    
    # Combine: prefer sources with known update dates
    sorted_sources = sources_with_dates + sources_without_dates
    
    # Display all available sources
    print(f"\n✓ Found {len(available_sources)} working source(s):")
    for i, src in enumerate(sorted_sources, 1):
        update_info = src["last_update"].strftime('%Y-%m-%d') if src["last_update"] else "unknown"
        marker = "➜ SELECTED" if i == 1 else ""
        print(f"  {i}. {src['source']['name']} - {src['count']} codes (updated: {update_info}) {marker}")
    
    # Use the most recently updated source (or most entries if no dates available)
    selected = sorted_sources[0]
    selection_reason = "most recently updated" if selected["last_update"] else "most entries"
    print(f"\n✓ Using {selection_reason} source: {selected['source']['name']}")
    print(f"  Total network codes: {selected['count']}")
    
    return selected["data"]


def parse_existing_file(existing_file):
    """Parse existing file preserving all structure, comments, and docstrings."""
    content = existing_file.read_text()
    
    # Extract the docstring
    docstring_match = re.match(r'^(""".*?""")', content, re.DOTALL)
    docstring = docstring_match.group(1) if docstring_match else ''
    
    # Find the NETWORK_OPERATORS dictionary
    dict_match = re.search(
        r'(NETWORK_OPERATORS\s*=\s*\{)(.*?)(\n\})',
        content,
        re.DOTALL
    )
    
    if not dict_match:
        print("Error: Could not find NETWORK_OPERATORS in existing file")
        return None, None, None
    
    dict_content = dict_match.group(2)
    
    # Parse entries while preserving comments and structure
    entries = {}
    lines_with_comments = []
    
    for line in dict_content.split('\n'):
        # Preserve comment lines
        if line.strip().startswith('#'):
            lines_with_comments.append(('comment', line))
        # Parse code entries
        else:
            match = re.match(r'\s*"(\d+)":\s*"([^"]+)",?', line)
            if match:
                code, name = match.group(1), match.group(2)
                entries[code] = name
                lines_with_comments.append(('entry', code, name))
            elif line.strip() == '':
                lines_with_comments.append(('blank', line))
    
    # Extract function definitions after the dict
    func_match = re.search(r'(\n\ndef get_network_name.*)', content, re.DOTALL)
    functions = func_match.group(1) if func_match else ''
    
    return docstring, entries, lines_with_comments, functions


def update_file_preserving_structure(existing_file, new_codes):
    """Update file while preserving docstrings, comments, and structure."""
    
    result = parse_existing_file(existing_file)
    if result[0] is None:
        return False
    
    docstring, existing_entries, structure, functions = result
    
    # Merge: existing entries take priority, add only truly new codes
    updated_entries = existing_entries.copy()
    added_count = 0
    
    for code, name in new_codes.items():
        if code not in updated_entries:
            updated_entries[code] = name
            added_count += 1
    
    if added_count == 0:
        print(f"  No new entries to add to {existing_file.name}")
        return False
    
    print(f"  Adding {added_count} new network codes to {existing_file.name}")
    
    # Rebuild the file with updated entries but preserving structure
    new_content_parts = [docstring, '\n\n']
    
    # Add comment about the database
    new_content_parts.append('# Comprehensive database of mobile network operators by MCC+MNC\n')
    new_content_parts.append('# Format: "MCCMNC": "Operator Name"\n')
    new_content_parts.append('NETWORK_OPERATORS = {\n')
    
    # Reconstruct with preserved comments and add new entries in appropriate sections
    current_section_codes = set()
    
    for item in structure:
        if item[0] == 'comment':
            # Write the comment
            new_content_parts.append(item[1] + '\n')
            current_section_codes.clear()
        elif item[0] == 'entry':
            code = item[1]
            # Use updated name if exists
            name = updated_entries.get(code, item[2])
            new_content_parts.append(f'    "{code}": "{name}",\n')
            current_section_codes.add(code)
        elif item[0] == 'blank':
            new_content_parts.append('\n')
    
    # Add any remaining new codes that don't fit in existing sections
    remaining_codes = set(updated_entries.keys()) - set(existing_entries.keys())
    if remaining_codes:
        new_content_parts.append('\n    # Additional network codes\n')
        for code in sorted(remaining_codes):
            new_content_parts.append(f'    "{code}": "{updated_entries[code]}",\n')
    
    new_content_parts.append('}\n')
    
    # Add function definitions if they exist
    if functions:
        new_content_parts.append(functions)
    
    existing_file.write_text(''.join(new_content_parts))
    return True


def main():
    """Main update process."""
    print("Fetching network operator data from public sources...")
    
    # Fetch data from the most recently updated available source
    new_codes = fetch_mcc_mnc_data()
    
    if not new_codes:
        print("\n✗ ERROR: Could not fetch data from any source!")
        sys.exit(1)
    
    # Update all network_codes.py files
    repo_root = Path(__file__).parent.parent.parent
    
    files_updated = False
    for target in [
        repo_root / "custom_components" / "legacy_gsm_sms" / "network_codes.py",
        repo_root / "addon-gsm-gateway" / "network_codes.py",
        repo_root / "network_codes.py"
    ]:
        if not target.exists():
            print(f"Warning: {target} does not exist, skipping")
            continue
        
        print(f"\nProcessing {target}...")
        if update_file_preserving_structure(target, new_codes):
            files_updated = True
    
    if files_updated:
        print("\n✓ Update complete! New network codes added.")
    else:
        print("\n✓ No updates needed - all network codes are already current.")


if __name__ == "__main__":
    main()
