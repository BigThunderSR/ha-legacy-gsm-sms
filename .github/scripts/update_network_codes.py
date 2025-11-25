#!/usr/bin/env python3
"""Update network operator codes from public sources."""

import json
import re
import sys
from datetime import datetime
from email.utils import parsedate_to_datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

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

# Wikipedia MVNO list pages (for reference - not currently used due to lack of MCC-MNC codes)
# When adding new MVNOs to MANUAL_OVERRIDES, check these pages for updates:
# - USA: https://en.wikipedia.org/wiki/List_of_United_States_mobile_virtual_network_operators
# - Canada: https://en.wikipedia.org/wiki/List_of_Canadian_mobile_virtual_network_operators  
# - Mexico: https://en.wikipedia.org/wiki/List_of_mobile_network_operators_of_the_Americas#Mexico
#
# To find MCC-MNC codes for MVNOs:
# 1. Check https://www.mcc-mnc.com/ or https://cellidfinder.com/mcc-mnc
# 2. Search the MVNO name + "MCC MNC" in Google
# 3. Check the FCC database for US carriers: https://www.fcc.gov/general/universal-licensing-system
WIKIPEDIA_MVNO_SOURCES = [
    {
        "url": "https://en.wikipedia.org/wiki/List_of_United_States_mobile_virtual_network_operators",
        "country": "USA",
        "mcc_prefixes": ["310", "311", "312", "313", "314", "315", "316"],
    },
    {
        "url": "https://en.wikipedia.org/wiki/List_of_Canadian_mobile_virtual_network_operators",
        "country": "Canada",
        "mcc_prefixes": ["302"],
    },
    {
        "url": "https://en.wikipedia.org/wiki/List_of_mobile_network_operators_of_the_Americas#Mexico",
        "country": "Mexico",
        "mcc_prefixes": ["334"],
    },
]

# Manual overrides for specific operator codes
# These corrections will be applied after fetching from sources
# to fix known issues in the upstream data or to preserve MVNO distinctions
#
# MAINTENANCE: To keep MVNO list current:
# 1. Periodically check Wikipedia MVNO pages (links above)
# 2. For new MVNOs, find their MCC-MNC codes using the resources listed above
# 3. Add entries below in the format: "MCCMNC": "Operator Name",  # Description
# 4. Run this script to update all network_codes.py files
MANUAL_OVERRIDES = {
    # USA MVNOs (MCC 310/311/312/313)
    "310053": "Virgin Mobile",  # T-Mobile MVNO (former Sprint)
    "310260": "T-Mobile",  # Main T-Mobile code (also used by Mint Mobile, Ting MVNOs)
    "310440": "Numerex",  # M2M MVNO
    "310640": "Numerex",  # M2M MVNO
    "310650": "Jasper",  # M2M MVNO (Jasper Technologies)
    "310840": "telna Mobile",  # MVNO (Telecom North America Mobile)
    "310850": "Aeris",  # M2M MVNO (Aeris Communications)
    "311280": "Assurance Wireless",  # Verizon MVNO (Lifeline service)
    "311660": "Metro by T-Mobile",  # Former MetroPCS, now T-Mobile MVNO brand
    "311870": "T-Mobile",  # Former Sprint MVNO services
    "311880": "T-Mobile",  # Former Sprint MVNO services
    "311900": "GigSky",  # International MVNO
    "311960": "Lycamobile",  # International MVNO
    "312210": "Aspenta International",  # MVNO
    "312300": "telna Mobile",  # MVNO (Telecom North America Mobile)
    "312690": "Tecore Global Services",  # MVNO
    "312870": "GigSky Mobile",  # International MVNO
    "313260": "Expeto Wireless",  # MVNO
    "313480": "Ready Wireless",  # MVNO
    "313760": "Hologram",  # IoT/M2M MVNO
    "313770": "Tango Extend",  # Tango Networks MVNO
    "314340": "e/marconi",  # MVNO (E-Marconi LLC)
    "314680": "Xfinity Mobile",  # Comcast MVNO
    "314720": "OXIO",  # MVNO
    "314730": "TextNow",  # MVNO
    "314790": "Neuner Mobile Technologies",  # MVNO
    
    # Canada MVNOs (MCC 302)
    "302100": "dotmobile",  # Data on Tap MVNO
    "302160": "Sugar Mobile",  # Iristel MVNO
    "302340": "Execulink",  # MVNO
    "302370": "Fido",  # Rogers MVNO (former Microcell)
    "302760": "Public Mobile",  # Telus MVNO
    
    # Mexico MVNOs (MCC 334)
    "334030": "Movistar",  # MVNO on AT&T
    "334110": "Maxcom Telecomunicaciones",  # MVNO
    "334120": "Quickly Phone",  # MVNO
    "334170": "OXIO Mobile",  # MVNO
    "334180": "FreedomPop",  # MVNO
    "334200": "Virgin Mobile",  # MVNO
    "334210": "YO Mobile",  # Yonder Media Mobile MVNO
    "334220": "Megamóvil",  # Mega Cable MVNO
    
    # Fix syntax errors from unescaped quotes in source data
    "24706": "SIA UNISTARS",  # Latvia - Source has broken quotes
    "24707": "SIA MEGATEL",   # Latvia - Source has broken quotes
    "25509": "PRJSC Farlep-Invest",  # Ukraine - Source has broken quotes
}


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


def scrape_wikipedia_mvnos():
    """Scrape MVNO information from Wikipedia pages.
    
    Returns:
        Dictionary mapping MCC-MNC codes to MVNO operator names
    """
    mvno_overrides = {}
    
    print("\nScraping MVNO data from Wikipedia...")
    
    # Use a proper User-Agent header to avoid 403 errors
    headers = {
        'User-Agent': (
            'Mozilla/5.0 (compatible; MCC-MNC-Updater/1.0; '
            '+https://github.com/BigThunderSR/ha-legacy-gsm-sms)'
        )
    }
    
    for wiki_source in WIKIPEDIA_MVNO_SOURCES:
        try:
            country = wiki_source['country']
            print(f"  Fetching {country} MVNOs from Wikipedia...")
            response = requests.get(
                wiki_source['url'], headers=headers, timeout=15
            )
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all tables in the page
            tables = soup.find_all('table', class_='wikitable')
            
            for table in tables:
                rows = table.find_all('tr')
                
                # Try to identify header columns
                headers = []
                if rows:
                    header_row = rows[0]
                    header_cells = header_row.find_all(['th', 'td'])
                    headers = [
                        th.get_text(strip=True).lower()
                        for th in header_cells
                    ]
                
                # Look for columns containing MCC, MNC, and operator name
                mcc_col = mnc_col = name_col = None
                for idx, header in enumerate(headers):
                    if 'mcc' in header:
                        mcc_col = idx
                    elif 'mnc' in header:
                        mnc_col = idx
                    elif any(
                        term in header
                        for term in ['operator', 'brand', 'name', 'mvno']
                    ):
                        if name_col is None:  # Use first name-like column
                            name_col = idx
                
                # Process data rows
                for row in rows[1:]:  # Skip header row
                    cells = row.find_all(['td', 'th'])
                    if len(cells) < 2:
                        continue
                    
                    mcc = mnc = name = None
                    
                    # Extract values based on identified columns
                    if mcc_col is not None and mcc_col < len(cells):
                        mcc = cells[mcc_col].get_text(strip=True)
                    if mnc_col is not None and mnc_col < len(cells):
                        mnc = cells[mnc_col].get_text(strip=True)
                    if name_col is not None and name_col < len(cells):
                        name = cells[name_col].get_text(strip=True)
                    
                    # If we didn't find columns by header, try pattern matching
                    if not mcc or not mnc or not name:
                        for cell in cells:
                            text = cell.get_text(strip=True)
                            # Look for MCC pattern
                            if re.match(r'^\d{3}$', text) and not mcc:
                                mcc = text
                            # Look for MNC pattern (after finding MCC)
                            elif (
                                re.match(r'^\d{2,3}$', text)
                                and mcc
                                and not mnc
                            ):
                                mnc = text
                            # Look for operator name
                            elif (
                                text
                                and not text.isdigit()
                                and len(text) > 2
                                and not name
                            ):
                                name = text
                    
                    # Clean up and validate
                    if mcc and mnc and name:
                        mcc = mcc.strip()
                        mnc = mnc.strip().zfill(2)  # Pad MNC to 2 digits
                        name = name.strip()
                        
                        # Validate MCC matches expected prefixes
                        if mcc in wiki_source['mcc_prefixes']:
                            code = f"{mcc}{mnc}"
                            # Only add if it's a valid 5-6 digit code
                            if 5 <= len(code) <= 6 and code.isdigit():
                                # Clean up common Wikipedia formatting
                                # Remove reference markers [1]
                                name = re.sub(r'\[\d+\]', '', name)
                                # Normalize whitespace
                                name = re.sub(r'\s+', ' ', name)
                                mvno_overrides[code] = name
            
            # Count codes found for this country
            prefixes = tuple(wiki_source['mcc_prefixes'])
            found = sum(
                1
                for code in mvno_overrides.keys()
                if code.startswith(prefixes)
            )
            if found > 0:
                print(f"    ✓ Found {found} {country} MVNO codes")
            else:
                print(f"    ⚠ No MVNOs found (table format may have changed)")
                
        except requests.exceptions.RequestException as e:
            print(f"    ✗ Failed to fetch {country} MVNOs: {e}")
        except Exception as e:
            print(f"    ✗ Error parsing {country} MVNOs: {e}")
    
    return mvno_overrides


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


def get_mcc_prefix(code):
    """Extract MCC prefix (first 3 digits) from a network code."""
    if len(code) >= 3:
        return code[:3]
    return None


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
        return None, None, None, None
    
    dict_content = dict_match.group(2)
    
    # Parse entries while preserving comments and structure
    entries = {}
    lines_with_comments = []
    sections = {}  # Track which MCC prefixes appear in which sections
    current_section_comment = None
    current_section_codes = set()
    
    for line in dict_content.split('\n'):
        # Preserve comment lines
        if line.strip().startswith('#'):
            # Save previous section if it exists
            if current_section_comment and current_section_codes:
                for code in current_section_codes:
                    mcc = get_mcc_prefix(code)
                    if mcc:
                        if mcc not in sections:
                            sections[mcc] = current_section_comment
            
            current_section_comment = line
            current_section_codes = set()
            lines_with_comments.append(('comment', line))
        # Parse code entries
        else:
            match = re.match(r'\s*"(\d+)":\s*"([^"]+)",?', line)
            if match:
                code, name = match.group(1), match.group(2)
                entries[code] = name
                current_section_codes.add(code)
                lines_with_comments.append(('entry', code, name))
            elif line.strip() == '':
                lines_with_comments.append(('blank', line))
    
    # Don't forget the last section
    if current_section_comment and current_section_codes:
        for code in current_section_codes:
            mcc = get_mcc_prefix(code)
            if mcc:
                if mcc not in sections:
                    sections[mcc] = current_section_comment
    
    # Extract function definitions after the dict
    func_match = re.search(r'(\n\ndef get_network_name.*)', content, re.DOTALL)
    functions = func_match.group(1) if func_match else ''
    
    return docstring, entries, lines_with_comments, functions, sections


def update_file_preserving_structure(existing_file, new_codes):
    """Update file while preserving docstrings, comments, and structure."""
    
    result = parse_existing_file(existing_file)
    if result[0] is None:
        return False
    
    docstring, existing_entries, structure, functions, sections = result
    
    # Separate new codes into truly new ones and updates to existing ones
    updated_entries = existing_entries.copy()
    new_entries = {}
    
    for code, name in new_codes.items():
        if code in existing_entries:
            # Code exists - check if name changed
            if existing_entries[code] != name:
                # Name changed - update it
                updated_entries[code] = name
        else:
            # Code doesn't exist - it's a new entry
            updated_entries[code] = name
            new_entries[code] = name
    
    if not new_entries:
        print(f"  No new entries to add to {existing_file.name}")
        return False
    
    # Count truly new codes vs updates
    truly_new = [c for c in new_entries.keys() if c not in existing_entries]
    updates = [c for c in new_entries.keys() if c in existing_entries]
    
    print(f"  Processing {len(truly_new)} new codes and {len(updates)} updates for "
          f"{existing_file.name}")
    
    # Group new entries by MCC prefix for insertion into correct sections
    new_by_mcc = {}
    orphaned_codes = []
    
    for code, name in new_entries.items():
        mcc = get_mcc_prefix(code)
        if mcc:
            if mcc in sections:
                # MCC section exists - add to that section
                if mcc not in new_by_mcc:
                    new_by_mcc[mcc] = []
                new_by_mcc[mcc].append((code, name))
            else:
                # MCC section doesn't exist - add to orphaned for later
                orphaned_codes.append((code, name))
        else:
            # No valid MCC prefix
            orphaned_codes.append((code, name))
    
    # Sort entries within each MCC group
    for mcc in new_by_mcc:
        new_by_mcc[mcc].sort(key=lambda x: x[0])
    
    # Group orphaned codes by MCC for better organization
    orphaned_by_mcc = {}
    for code, name in orphaned_codes:
        mcc = get_mcc_prefix(code)
        if mcc:
            if mcc not in orphaned_by_mcc:
                orphaned_by_mcc[mcc] = []
            orphaned_by_mcc[mcc].append((code, name))
        else:
            # Truly orphaned (no valid MCC)
            if 'unknown' not in orphaned_by_mcc:
                orphaned_by_mcc['unknown'] = []
            orphaned_by_mcc['unknown'].append((code, name))
    
    # Sort orphaned codes
    for mcc in orphaned_by_mcc:
        orphaned_by_mcc[mcc].sort(key=lambda x: x[0])
    
    # Rebuild the file with updated entries but preserving structure
    new_content_parts = [docstring, '\n\n']
    
    # Add comment about the database
    new_content_parts.append(
        '# Comprehensive database of mobile network operators by MCC+MNC\n'
    )
    new_content_parts.append('# Format: "MCCMNC": "Operator Name"\n')
    new_content_parts.append('NETWORK_OPERATORS = {\n')
    
    # Reconstruct with preserved comments and insert new entries
    # in correct numerical order within their sections
    current_section_mcc = None
    section_entries_added = set()
    pending_new_codes = []  # Track new codes to insert in this section
    
    for i, item in enumerate(structure):
        if item[0] == 'comment':
            # Before writing this comment, finalize any pending section
            if current_section_mcc and current_section_mcc in new_by_mcc:
                section_entries_added.add(current_section_mcc)
            
            # Write the comment
            new_content_parts.append(item[1] + '\n')
            
            # Determine which MCC section this comment represents
            # For multi-MCC sections (e.g., "United States (MCC 310-316)"),
            # we need to load codes for ALL MCCs that map to this section
            current_section_mcc = None
            pending_new_codes = []
            for mcc, comment in sections.items():
                if comment == item[1]:
                    # Set current_section_mcc to the first MCC we find
                    if current_section_mcc is None:
                        current_section_mcc = mcc
                    # Add codes from this MCC to pending_new_codes
                    if mcc in new_by_mcc:
                        pending_new_codes.extend(new_by_mcc[mcc])
            
            # Sort pending codes by code number for correct insertion order
            if pending_new_codes:
                pending_new_codes.sort(key=lambda x: x[0])
            
        elif item[0] == 'entry':
            code = item[1]
            mcc = get_mcc_prefix(code)
            
            # Check if this code's MCC belongs to the current section
            code_section = sections.get(mcc)
            in_current_section = (code_section and current_section_mcc and
                                  code_section == sections.get(current_section_mcc))
            
            # Insert any pending new codes that come before this code
            # in numerical order (only if in the same section)
            if pending_new_codes and in_current_section:
                codes_to_insert = []
                remaining_codes = []
                
                for new_code, new_name in pending_new_codes:
                    if new_code < code:
                        codes_to_insert.append((new_code, new_name))
                    else:
                        remaining_codes.append((new_code, new_name))
                
                # Insert codes that come before current code
                for new_code, new_name in codes_to_insert:
                    new_content_parts.append(
                        f'    "{new_code}": "{new_name}",\n'
                    )
                
                # Update pending list with remaining codes
                pending_new_codes = remaining_codes
            
            # Write the current entry
            name = updated_entries.get(code, item[2])
            new_content_parts.append(f'    "{code}": "{name}",\n')
            
            # Check if this is the last entry in this section
            is_last_in_section = False
            if i + 1 < len(structure):
                next_item = structure[i + 1]
                if next_item[0] == 'comment':
                    is_last_in_section = True
                elif next_item[0] == 'blank':
                    if (i + 2 < len(structure) and
                            structure[i + 2][0] == 'comment'):
                        is_last_in_section = True
            else:
                is_last_in_section = True
            
            # If last entry in section, add any remaining pending codes
            if (is_last_in_section and pending_new_codes and in_current_section):
                for new_code, new_name in pending_new_codes:
                    new_content_parts.append(
                        f'    "{new_code}": "{new_name}",\n'
                    )
                pending_new_codes = []
                if current_section_mcc:
                    section_entries_added.add(current_section_mcc)
                
        elif item[0] == 'blank':
            new_content_parts.append('\n')
    
    # Add orphaned codes (codes without existing MCC sections) organized by MCC
    if orphaned_by_mcc:
        total_orphaned = sum(len(codes) for codes in orphaned_by_mcc.values())
        print(f"    Adding {total_orphaned} codes in new MCC sections")
        new_content_parts.append('\n    # Additional network codes (new MCC regions)\n')
        
        # Sort MCCs for consistent ordering
        sorted_mccs = sorted([m for m in orphaned_by_mcc.keys() if m != 'unknown'])
        if 'unknown' in orphaned_by_mcc:
            sorted_mccs.append('unknown')
        
        for mcc in sorted_mccs:
            codes = orphaned_by_mcc[mcc]
            if mcc == 'unknown':
                new_content_parts.append('\n    # Unclassified codes\n')
            else:
                # Add a basic comment for the new MCC section
                new_content_parts.append(f'\n    # MCC {mcc}\n')
            
            for code, name in codes:
                new_content_parts.append(f'    "{code}": "{name}",\n')
    
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
    
    # Wikipedia scraping is currently disabled because Wikipedia MVNO pages
    # don't include MCC-MNC codes in a machine-readable format.
    # MVNOs must be maintained manually in the MANUAL_OVERRIDES dictionary.
    # See comments above WIKIPEDIA_MVNO_SOURCES for resources to find new MVNOs.
    wikipedia_mvnos = {}
    
    # Uncomment to enable Wikipedia scraping (experimental):
    # try:
    #     wikipedia_mvnos = scrape_wikipedia_mvnos()
    # except Exception as e:
    #     print(f"\n⚠ Wikipedia scraping failed: {e}")
    #     print("  Continuing with manual overrides only...")
    
    # Merge Wikipedia MVNOs with manual overrides
    # Manual overrides take precedence over Wikipedia data
    all_overrides = {}
    if wikipedia_mvnos:
        all_overrides.update(wikipedia_mvnos)  # Add Wikipedia data first
    all_overrides.update(MANUAL_OVERRIDES)  # Manual overrides win
    
    # Apply all overrides to correct known issues in source data
    wiki_count = len(wikipedia_mvnos)
    manual_count = len(MANUAL_OVERRIDES)
    total_corrections = len(all_overrides)
    
    if wiki_count > 0:
        print(
            f"\nApplying {total_corrections} corrections "
            f"({wiki_count} from Wikipedia, {manual_count} manual)..."
        )
    else:
        print(f"\nApplying {manual_count} manual corrections...")
    
    for code, corrected_name in all_overrides.items():
        if code in new_codes:
            old_name = new_codes[code]
            if old_name != corrected_name:
                new_codes[code] = corrected_name
                print(f"  {code}: '{old_name}' → '{corrected_name}'")
        else:
            # Code doesn't exist in source data, add it
            new_codes[code] = corrected_name
            print(f"  {code}: Added '{corrected_name}' (missing from source)")
    
    # Update all network_codes.py files
    repo_root = Path(__file__).parent.parent.parent
    
    files_updated = False
    for target in [
        repo_root / "custom_components" / "legacy_gsm_sms" / "network_codes.py",
        repo_root / "addon-gsm-gateway" / "network_codes.py",
        repo_root / "addon-test-current" / "network_codes.py",
        repo_root / "addon-test-pavelve" / "network_codes.py",
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
