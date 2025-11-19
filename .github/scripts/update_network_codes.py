#!/usr/bin/env python3
"""Update network operator codes from public sources."""

import json
import re
import sys
from pathlib import Path

import requests

# Public data sources
SOURCES = {
    # MCC list from ITU
    "mcc": "https://www.itu.int/dms_pub/itu-t/opb/sp/T-SP-E.212B-2017-PDF-E.pdf",
    
    # Community-maintained database (example - replace with actual source)
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


def merge_with_existing(new_codes, existing_file):
    """Merge new codes with existing database, preserving manual additions."""
    # Read existing file
    existing_content = existing_file.read_text()
    
    # Extract existing NETWORK_OPERATORS dict
    match = re.search(
        r'NETWORK_OPERATORS = \{(.*?)\}',
        existing_content,
        re.DOTALL
    )
    
    if not match:
        print("Error: Could not find NETWORK_OPERATORS in existing file")
        return None
    
    existing_dict_str = match.group(1)
    
    # Parse existing entries (simple regex approach)
    existing_codes = {}
    for line in existing_dict_str.split('\n'):
        match = re.match(r'\s*"(\d+)":\s*"([^"]+)",?', line)
        if match:
            existing_codes[match.group(1)] = match.group(2)
    
    # Merge: new codes override, but keep manual additions
    merged = existing_codes.copy()
    merged.update(new_codes)
    
    return merged


def generate_network_codes_file(codes_dict, output_file):
    """Generate the network_codes.py file with updated data."""
    
    # Group by region for better organization
    us_codes = {k: v for k, v in sorted(codes_dict.items()) if k.startswith(('310', '311', '312', '313', '316'))}
    ca_codes = {k: v for k, v in sorted(codes_dict.items()) if k.startswith('302')}
    other_codes = {k: v for k, v in sorted(codes_dict.items()) if not k.startswith(('310', '311', '312', '313', '316', '302'))}
    
    content = '''"""Network operator name lookup by MCC+MNC code."""

# Comprehensive database of mobile network operators by MCC+MNC
# Auto-updated from public sources with manual additions
# Last updated: {date}

NETWORK_OPERATORS = {{
    # United States (MCC 310-316)
{us_entries}
    
    # Canada (MCC 302)
{ca_entries}
    
    # International
{other_entries}
}}


def get_network_name(network_code: str):
    """Get network operator name from MCC+MNC code.
    
    Args:
        network_code: MCC+MNC code (e.g., "310260" for T-Mobile USA)
        
    Returns:
        Network operator name or None if not found
    """
    if not network_code:
        return None
    return NETWORK_OPERATORS.get(network_code)
'''
    
    from datetime import datetime
    
    def format_entries(codes):
        return '\n'.join([f'    "{code}": "{name}",' for code, name in codes.items()])
    
    final_content = content.format(
        date=datetime.now().strftime('%Y-%m-%d'),
        us_entries=format_entries(us_codes),
        ca_entries=format_entries(ca_codes),
        other_entries=format_entries(other_codes)
    )
    
    output_file.write_text(final_content)
    print(f"Updated {output_file}")


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
    
    # Update both files
    repo_root = Path(__file__).parent.parent.parent
    
    for target in [
        repo_root / "custom_components" / "legacy_gsm_sms" / "network_codes.py",
        repo_root / "network_codes.py"
    ]:
        if not target.exists():
            print(f"Warning: {target} does not exist, skipping")
            continue
        
        # Merge with existing
        merged_codes = merge_with_existing(new_codes, target)
        
        if merged_codes:
            # Generate new file
            generate_network_codes_file(merged_codes, target)
    
    print("Update complete!")


if __name__ == "__main__":
    main()
