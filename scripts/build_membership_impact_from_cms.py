#!/usr/bin/env python3
"""
Build membership impact report from CMS Monthly Enrollment data.

This script downloads CMS enrollment data for November and December 2025,
processes it to create org_cd aggregations, and generates a membership impact
CSV matching the chatbot schema.
"""

import os
import requests
import zipfile
import pandas as pd
import numpy as np
from pathlib import Path

# URLs for CMS data
NOV_URL = "https://www.cms.gov/files/zip/monthly-enrollment-cpsc-november-2025.zip"
DEC_URL = "https://www.cms.gov/files/zip/monthly-enrollment-cpsc-december-2025.zip"

# Output paths
DATA_DIR = Path(__file__).parent.parent / "data"
TEMP_DIR = DATA_DIR / "temp"
OUTPUT_FILE = DATA_DIR / "membership_impact_report_cms_100_orgs.csv"

def download_and_extract(url, extract_to):
    """Download zip file and extract to directory."""
    print(f"Downloading {url}...")
    
    # Create the extraction directory
    extract_to.mkdir(parents=True, exist_ok=True)
    
    response = requests.get(url)
    response.raise_for_status()

    zip_path = extract_to / "temp.zip"
    with open(zip_path, 'wb') as f:
        f.write(response.content)

    print("Extracting...")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)
        print(f"Extracted files: {zip_ref.namelist()}")

    # Find the CSV file (look recursively)
    csv_files = list(extract_to.rglob("*.csv"))
    if not csv_files:
        # List all files to debug
        all_files = list(extract_to.rglob("*"))
        print(f"All extracted files: {[str(f) for f in all_files]}")
        raise FileNotFoundError(f"No CSV found in {extract_to}")

    return csv_files[0]

def process_cms_file(csv_path):
    """Process CMS CSV file and return aggregated enrollment by org_cd."""
    print(f"Processing {csv_path}...")

    # Read CSV with low_memory=False to handle large files
    df = pd.read_csv(csv_path, low_memory=False)

    # Normalize column names to lowercase
    df.columns = df.columns.str.lower()
    
    print(f"Available columns: {list(df.columns)}")
    print(f"Sample data:\n{df.head()}")

    # Create org_cd: contract_id + "_" + plan_id (if plan_id exists)
    # Look for contract/plan related columns
    contract_cols = [col for col in df.columns if 'contract' in col]
    plan_cols = [col for col in df.columns if 'plan' in col]
    
    print(f"Contract columns: {contract_cols}")
    print(f"Plan columns: {plan_cols}")
    
    if contract_cols:
        contract_col = contract_cols[0]
    else:
        raise ValueError(f"No contract column found in {csv_path}")
    
    if plan_cols:
        plan_col = plan_cols[0]
        df['org_cd'] = df[contract_col].astype(str) + "_" + df[plan_col].astype(str)
    else:
        df['org_cd'] = df[contract_col].astype(str)

    # Find enrollment column and convert to numeric
    if 'enrollment' in df.columns:
        enrollment_col = 'enrollment'
    elif 'mbr_cnt' in df.columns:
        enrollment_col = 'mbr_cnt'
    else:
        # Look for enrollment-like column
        enroll_cols = [col for col in df.columns if 'enroll' in col.lower() or 'mbr' in col.lower() or 'count' in col.lower()]
        if enroll_cols:
            enrollment_col = enroll_cols[0]
            print(f"Using enrollment column: {enrollment_col}")
        else:
            raise ValueError(f"Could not find enrollment column in {csv_path}. Available: {list(df.columns)}")
    
    # Convert enrollment to numeric, treating '*' as 0
    df[enrollment_col] = pd.to_numeric(df[enrollment_col], errors='coerce').fillna(0)

    # Aggregate by org_cd
    aggregated = df.groupby('org_cd')[enrollment_col].sum().reset_index()
    aggregated = aggregated.rename(columns={enrollment_col: 'total_enrollment'})

    return aggregated

def main():
    """Main processing function."""
    # Create directories
    DATA_DIR.mkdir(exist_ok=True)
    TEMP_DIR.mkdir(exist_ok=True)

    try:
        # Download and process November data
        nov_csv = download_and_extract(NOV_URL, TEMP_DIR / "nov")
        nov_data = process_cms_file(nov_csv)
        nov_data = nov_data.rename(columns={'total_enrollment': 'mbr_cnt_x202511_prd'})

        # Download and process December data
        dec_csv = download_and_extract(DEC_URL, TEMP_DIR / "dec")
        dec_data = process_cms_file(dec_csv)
        dec_data = dec_data.rename(columns={'total_enrollment': 'mbr_cnt_x202512_prd'})

        # Merge the two months
        merged = pd.merge(nov_data, dec_data, on='org_cd', how='outer').fillna(0)
        
        # Ensure numeric types
        merged['mbr_cnt_x202511_prd'] = pd.to_numeric(merged['mbr_cnt_x202511_prd'], errors='coerce').fillna(0)
        merged['mbr_cnt_x202512_prd'] = pd.to_numeric(merged['mbr_cnt_x202512_prd'], errors='coerce').fillna(0)

        # Select top 100 orgs by November enrollment (deterministic)
        top_100 = merged.nlargest(100, 'mbr_cnt_x202511_prd')['org_cd'].tolist()

        # Filter to top 100
        df = merged[merged['org_cd'].isin(top_100)].copy()

        # Compute required metrics
        df['dropped_mbr_cnt_x202512m01_prd_vs_x202511m12_prd'] = (
            df['mbr_cnt_x202511_prd'] - df['mbr_cnt_x202512_prd']
        ).clip(lower=0)

        df['new_mbr_cnt_x202512m01_prd_vs_x202511m12_prd'] = (
            df['mbr_cnt_x202512_prd'] - df['mbr_cnt_x202511_prd']
        ).clip(lower=0)

        df['com_mbr_cnt_x202512m01_prd_vs_x202511m12_prd'] = (
            df['mbr_cnt_x202512_prd'] - df['mbr_cnt_x202511_prd']
        )

        # Calculate percentages (avoid division by zero)
        df['dropped_per'] = np.where(
            df['mbr_cnt_x202511_prd'] > 0,
            (df['dropped_mbr_cnt_x202512m01_prd_vs_x202511m12_prd'] / df['mbr_cnt_x202511_prd']) * 100,
            np.nan
        )

        df['new_members_percentage'] = np.where(
            df['mbr_cnt_x202511_prd'] > 0,
            (df['new_mbr_cnt_x202512m01_prd_vs_x202511m12_prd'] / df['mbr_cnt_x202511_prd']) * 100,
            np.nan
        )

        # Add placeholder columns to match chatbot schema
        df['moved_from_org_cd'] = None
        df['moved_to_org_cd'] = None
        df['retro_term_mem_count'] = 0
        df['retro_add_mem_count'] = 0
        df['Potential_Reason_ctr'] = None
        df['Potential_Reason_mbrship_changes'] = None

        # Reorder columns to match expected schema
        column_order = [
            'org_cd',
            'mbr_cnt_x202511_prd',
            'mbr_cnt_x202512_prd',
            'dropped_mbr_cnt_x202512m01_prd_vs_x202511m12_prd',
            'new_mbr_cnt_x202512m01_prd_vs_x202511m12_prd',
            'com_mbr_cnt_x202512m01_prd_vs_x202511m12_prd',
            'dropped_per',
            'new_members_percentage',
            'moved_from_org_cd',
            'moved_to_org_cd',
            'retro_term_mem_count',
            'retro_add_mem_count',
            'Potential_Reason_ctr',
            'Potential_Reason_mbrship_changes'
        ]

        df = df[column_order]

        # Save to CSV
        df.to_csv(OUTPUT_FILE, index=False)
        print(f"✅ Generated {OUTPUT_FILE} with {len(df)} organizations")
        print(f"Sample data:\n{df.head()}")

    finally:
        # Clean up temp files
        import shutil
        if TEMP_DIR.exists():
            shutil.rmtree(TEMP_DIR)

if __name__ == "__main__":
    main()