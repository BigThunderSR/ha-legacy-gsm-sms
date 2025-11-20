#!/usr/bin/env python3
"""Update network operator codes from public sources."""

import json
import re
import sys
from pathlib import Path

import requests

# Public data sources
SOURCES = {
    # Community-maintained database
    "mcc_mnc_json": "https://raw.githubusercontent.com/musalbas/mcc-mnc-list/master/mcc-mnc-list.json",
}


def fetch_mcc_mnc_json():
    """Fetch MCC-MNC data from JSON source."""
    try:
        response = requests.get(SOURCES["mcc_mnc_json"], timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Warning: Failed to fetch JSON data: {e}")
        return []


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
    
    # Fetch data from JSON source
    json_data = fetch_mcc_mnc_json()
    
    # Convert to our format
    new_codes = {}
    for entry in json_data:
        mcc = entry.get('mcc', '')
        mnc = entry.get('mnc', '')
        operator = entry.get('network', '') or entry.get('brand', '')
        
        if mcc and mnc and operator:
            # Pad MNC to 2-3 digits as needed
            code = f"{mcc}{mnc.zfill(2)}"
            new_codes[code] = operator
    
    print(f"Found {len(new_codes)} network codes from public sources")
    
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
