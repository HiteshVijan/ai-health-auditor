#!/usr/bin/env python3
"""
Download and process medical coding data from free public sources.

This script downloads:
1. ICD-10-CM codes from CMS
2. HCPCS codes from CMS
3. Medicare Physician Fee Schedule

All data is from US Government sources and is in the public domain.
"""

import os
import sys
import csv
import json
import zipfile
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional
from io import BytesIO

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Base directory for data
DATA_DIR = Path(__file__).parent.parent / "data"

# CMS Data URLs (updated annually)
CMS_URLS = {
    # ICD-10-CM 2024 Code Files
    "icd10_codes": "https://www.cms.gov/files/zip/2024-code-descriptions-tabular-order-updated-01112024.zip",
    # HCPCS 2024 Annual Update
    "hcpcs_codes": "https://www.cms.gov/files/zip/2024-alpha-numeric-hcpcs-file.zip",
    # Medicare Physician Fee Schedule - National Payment Amount
    "fee_schedule": "https://www.cms.gov/files/zip/cy2024-physician-fee-schedule-national-payment-amount-file.zip",
}

# Fallback local sample data in case downloads fail
SAMPLE_ICD10_CODES = {
    "A00": {"description": "Cholera", "category": "Infectious Diseases"},
    "A01": {"description": "Typhoid and paratyphoid fevers", "category": "Infectious Diseases"},
    "E11": {"description": "Type 2 diabetes mellitus", "category": "Endocrine"},
    "I10": {"description": "Essential (primary) hypertension", "category": "Circulatory"},
    "J06": {"description": "Acute upper respiratory infections", "category": "Respiratory"},
    "K21": {"description": "Gastro-esophageal reflux disease", "category": "Digestive"},
    "M54": {"description": "Dorsalgia (back pain)", "category": "Musculoskeletal"},
    "R10": {"description": "Abdominal and pelvic pain", "category": "Symptoms"},
    "Z00": {"description": "General examination", "category": "Factors influencing health"},
}

SAMPLE_CPT_CODES = {
    # Evaluation and Management
    "99211": {"description": "Office visit, minimal", "category": "E/M", "rvu": 0.18, "fair_price": 30.0},
    "99212": {"description": "Office visit, straightforward", "category": "E/M", "rvu": 0.93, "fair_price": 65.0},
    "99213": {"description": "Office visit, low complexity", "category": "E/M", "rvu": 1.30, "fair_price": 110.0},
    "99214": {"description": "Office visit, moderate complexity", "category": "E/M", "rvu": 1.92, "fair_price": 165.0},
    "99215": {"description": "Office visit, high complexity", "category": "E/M", "rvu": 2.80, "fair_price": 240.0},
    # Hospital Visits
    "99221": {"description": "Initial hospital care, low", "category": "Hospital", "rvu": 1.92, "fair_price": 165.0},
    "99222": {"description": "Initial hospital care, moderate", "category": "Hospital", "rvu": 2.61, "fair_price": 225.0},
    "99223": {"description": "Initial hospital care, high", "category": "Hospital", "rvu": 3.86, "fair_price": 330.0},
    # Lab Tests
    "80048": {"description": "Basic metabolic panel", "category": "Lab", "rvu": 0.0, "fair_price": 25.0},
    "80053": {"description": "Comprehensive metabolic panel", "category": "Lab", "rvu": 0.0, "fair_price": 35.0},
    "80061": {"description": "Lipid panel", "category": "Lab", "rvu": 0.0, "fair_price": 40.0},
    "81001": {"description": "Urinalysis, automated", "category": "Lab", "rvu": 0.0, "fair_price": 12.0},
    "85025": {"description": "Complete blood count (CBC)", "category": "Lab", "rvu": 0.0, "fair_price": 20.0},
    "85027": {"description": "CBC, automated", "category": "Lab", "rvu": 0.0, "fair_price": 15.0},
    "87880": {"description": "Strep test, rapid", "category": "Lab", "rvu": 0.0, "fair_price": 25.0},
    # Imaging
    "70553": {"description": "MRI brain with/without contrast", "category": "Imaging", "rvu": 3.50, "fair_price": 1500.0},
    "71046": {"description": "Chest X-ray, 2 views", "category": "Imaging", "rvu": 0.22, "fair_price": 75.0},
    "72148": {"description": "MRI lumbar spine without contrast", "category": "Imaging", "rvu": 1.54, "fair_price": 1200.0},
    "73721": {"description": "MRI joint lower extremity", "category": "Imaging", "rvu": 1.54, "fair_price": 1100.0},
    "74177": {"description": "CT abdomen/pelvis with contrast", "category": "Imaging", "rvu": 3.20, "fair_price": 800.0},
    # Cardiology
    "93000": {"description": "Electrocardiogram (ECG/EKG)", "category": "Cardiology", "rvu": 0.17, "fair_price": 50.0},
    "93306": {"description": "Echocardiography, complete", "category": "Cardiology", "rvu": 1.30, "fair_price": 450.0},
    # Surgery
    "27447": {"description": "Total knee replacement", "category": "Surgery", "rvu": 20.79, "fair_price": 25000.0},
    "27130": {"description": "Total hip replacement", "category": "Surgery", "rvu": 20.79, "fair_price": 28000.0},
    "43239": {"description": "Upper GI endoscopy with biopsy", "category": "Surgery", "rvu": 3.50, "fair_price": 1500.0},
    "45380": {"description": "Colonoscopy with biopsy", "category": "Surgery", "rvu": 4.43, "fair_price": 2000.0},
    # Emergency
    "99281": {"description": "ED visit, self-limited", "category": "Emergency", "rvu": 0.45, "fair_price": 150.0},
    "99282": {"description": "ED visit, low urgency", "category": "Emergency", "rvu": 0.93, "fair_price": 250.0},
    "99283": {"description": "ED visit, moderate", "category": "Emergency", "rvu": 1.60, "fair_price": 400.0},
    "99284": {"description": "ED visit, high urgency", "category": "Emergency", "rvu": 2.74, "fair_price": 650.0},
    "99285": {"description": "ED visit, life-threatening", "category": "Emergency", "rvu": 4.00, "fair_price": 1000.0},
    # Injections/Infusions
    "96372": {"description": "Therapeutic injection", "category": "Injection", "rvu": 0.17, "fair_price": 35.0},
    "96374": {"description": "IV push, single drug", "category": "Infusion", "rvu": 0.21, "fair_price": 100.0},
    "96413": {"description": "Chemotherapy IV infusion", "category": "Infusion", "rvu": 0.60, "fair_price": 250.0},
    # Anesthesia
    "00100": {"description": "Anesthesia, salivary gland", "category": "Anesthesia", "rvu": 5.0, "fair_price": 400.0},
    "00400": {"description": "Anesthesia, skin surgery", "category": "Anesthesia", "rvu": 3.0, "fair_price": 300.0},
}

# Indian Healthcare Rates (CGHS 2024 rates - sample)
CGHS_RATES = {
    "consultation": {
        "general_physician": 300.0,
        "specialist": 500.0,
        "super_specialist": 800.0,
    },
    "procedures": {
        "ecg": 200.0,
        "xray_chest": 250.0,
        "ultrasound_abdomen": 800.0,
        "ct_scan_head": 3500.0,
        "mri_brain": 8000.0,
        "cbc": 150.0,
        "lipid_profile": 400.0,
        "thyroid_profile": 500.0,
    },
    "surgeries": {
        "appendectomy": 25000.0,
        "cholecystectomy": 35000.0,
        "hernia_repair": 25000.0,
        "cataract_surgery": 20000.0,
        "knee_replacement": 150000.0,
        "hip_replacement": 175000.0,
        "cabg": 200000.0,
        "angioplasty": 100000.0,
    },
    "room_charges": {
        "general_ward": 1500.0,
        "semi_private": 3000.0,
        "private": 5000.0,
        "icu": 8000.0,
    },
}


def ensure_directories() -> None:
    """Create necessary data directories."""
    dirs = [
        DATA_DIR / "icd10",
        DATA_DIR / "hcpcs",
        DATA_DIR / "cpt",
        DATA_DIR / "fee_schedules",
        DATA_DIR / "indian_rates",
        DATA_DIR / "processed",
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
        logger.info(f"Directory ready: {d}")


def download_file(url: str, dest_path: Path, timeout: int = 60) -> bool:
    """
    Download a file from URL.
    
    Args:
        url: Source URL
        dest_path: Destination path
        timeout: Request timeout in seconds
        
    Returns:
        bool: True if download successful
    """
    try:
        logger.info(f"Downloading: {url}")
        response = requests.get(url, timeout=timeout, stream=True)
        response.raise_for_status()
        
        with open(dest_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        logger.info(f"Downloaded to: {dest_path}")
        return True
        
    except requests.RequestException as e:
        logger.warning(f"Download failed: {e}")
        return False


def extract_zip(zip_path: Path, dest_dir: Path) -> list[Path]:
    """
    Extract a ZIP file.
    
    Args:
        zip_path: Path to ZIP file
        dest_dir: Destination directory
        
    Returns:
        List of extracted file paths
    """
    extracted = []
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(dest_dir)
            extracted = [dest_dir / name for name in zf.namelist()]
        logger.info(f"Extracted {len(extracted)} files to {dest_dir}")
    except zipfile.BadZipFile as e:
        logger.error(f"Failed to extract {zip_path}: {e}")
    return extracted


def download_icd10_codes() -> dict:
    """
    Download and parse ICD-10-CM codes from CMS.
    
    Returns:
        dict: Parsed ICD-10 codes
    """
    logger.info("=== Downloading ICD-10-CM Codes ===")
    
    icd10_dir = DATA_DIR / "icd10"
    zip_path = icd10_dir / "icd10_codes.zip"
    
    # Try to download from CMS
    if download_file(CMS_URLS["icd10_codes"], zip_path):
        extract_zip(zip_path, icd10_dir)
        # Parse the extracted files
        codes = parse_icd10_files(icd10_dir)
        if codes:
            save_processed_data("icd10_codes.json", codes)
            return codes
    
    # Fallback to sample data
    logger.warning("Using sample ICD-10 data (download failed)")
    save_processed_data("icd10_codes.json", SAMPLE_ICD10_CODES)
    return SAMPLE_ICD10_CODES


def parse_icd10_files(directory: Path) -> dict:
    """
    Parse ICD-10 code files from CMS format.
    
    Args:
        directory: Directory containing extracted files
        
    Returns:
        dict: Parsed codes
    """
    codes = {}
    
    # Look for the code description file (usually .txt format)
    for txt_file in directory.glob("*.txt"):
        try:
            with open(txt_file, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if not line or len(line) < 8:
                        continue
                    
                    # CMS format: Code (first 7 chars) + Description
                    code = line[:7].strip()
                    description = line[7:].strip()
                    
                    if code and description:
                        codes[code] = {
                            "description": description,
                            "category": _get_icd10_category(code),
                        }
            
            if codes:
                logger.info(f"Parsed {len(codes)} ICD-10 codes from {txt_file.name}")
                break
                
        except Exception as e:
            logger.error(f"Error parsing {txt_file}: {e}")
    
    return codes


def _get_icd10_category(code: str) -> str:
    """Get ICD-10 category from code prefix."""
    prefix = code[0].upper()
    categories = {
        "A": "Infectious Diseases",
        "B": "Infectious Diseases", 
        "C": "Neoplasms",
        "D": "Blood Diseases",
        "E": "Endocrine/Metabolic",
        "F": "Mental Disorders",
        "G": "Nervous System",
        "H": "Eye/Ear",
        "I": "Circulatory",
        "J": "Respiratory",
        "K": "Digestive",
        "L": "Skin",
        "M": "Musculoskeletal",
        "N": "Genitourinary",
        "O": "Pregnancy",
        "P": "Perinatal",
        "Q": "Congenital",
        "R": "Symptoms",
        "S": "Injury",
        "T": "Injury/Poisoning",
        "V": "External Causes",
        "W": "External Causes",
        "X": "External Causes",
        "Y": "External Causes",
        "Z": "Factors Influencing Health",
    }
    return categories.get(prefix, "Other")


def download_hcpcs_codes() -> dict:
    """
    Download and parse HCPCS codes from CMS.
    
    Returns:
        dict: Parsed HCPCS codes
    """
    logger.info("=== Downloading HCPCS Codes ===")
    
    hcpcs_dir = DATA_DIR / "hcpcs"
    zip_path = hcpcs_dir / "hcpcs_codes.zip"
    
    # Try to download from CMS
    if download_file(CMS_URLS["hcpcs_codes"], zip_path):
        extract_zip(zip_path, hcpcs_dir)
        codes = parse_hcpcs_files(hcpcs_dir)
        if codes:
            save_processed_data("hcpcs_codes.json", codes)
            return codes
    
    # Fallback to sample CPT data
    logger.warning("Using sample HCPCS/CPT data (download failed)")
    save_processed_data("hcpcs_codes.json", SAMPLE_CPT_CODES)
    return SAMPLE_CPT_CODES


def parse_hcpcs_files(directory: Path) -> dict:
    """
    Parse HCPCS code files from CMS format.
    
    Args:
        directory: Directory containing extracted files
        
    Returns:
        dict: Parsed codes
    """
    codes = {}
    
    # Look for Excel or CSV files
    for data_file in list(directory.glob("*.xlsx")) + list(directory.glob("*.csv")):
        try:
            import pandas as pd
            
            if data_file.suffix == ".xlsx":
                df = pd.read_excel(data_file)
            else:
                df = pd.read_csv(data_file)
            
            # Find code and description columns
            code_col = None
            desc_col = None
            
            for col in df.columns:
                col_lower = str(col).lower()
                if "hcpc" in col_lower or "code" in col_lower:
                    code_col = col
                elif "description" in col_lower or "long" in col_lower:
                    desc_col = col
            
            if code_col and desc_col:
                for _, row in df.iterrows():
                    code = str(row[code_col]).strip()
                    desc = str(row[desc_col]).strip()
                    if code and desc and code != "nan":
                        codes[code] = {
                            "description": desc,
                            "category": _get_hcpcs_category(code),
                        }
            
            if codes:
                logger.info(f"Parsed {len(codes)} HCPCS codes from {data_file.name}")
                break
                
        except Exception as e:
            logger.error(f"Error parsing {data_file}: {e}")
    
    return codes


def _get_hcpcs_category(code: str) -> str:
    """Get HCPCS category from code."""
    if not code:
        return "Other"
    
    first_char = code[0].upper()
    
    # CPT codes (numeric) 
    if first_char.isdigit():
        code_num = int(code[:5]) if len(code) >= 5 else int(code)
        if 99201 <= code_num <= 99499:
            return "E/M"
        elif 100 <= code_num <= 1999:
            return "Anesthesia"
        elif 10000 <= code_num <= 69999:
            return "Surgery"
        elif 70000 <= code_num <= 79999:
            return "Radiology"
        elif 80000 <= code_num <= 89999:
            return "Pathology/Lab"
        elif 90000 <= code_num <= 99999:
            return "Medicine"
    
    # HCPCS Level II (alpha-numeric)
    else:
        categories = {
            "A": "Transportation/Medical Supplies",
            "B": "Enteral/Parenteral",
            "C": "Hospital Outpatient",
            "D": "Dental",
            "E": "Durable Medical Equipment",
            "G": "Procedures/Services",
            "H": "Behavioral Health",
            "J": "Drugs",
            "K": "DME (Temporary)",
            "L": "Orthotics/Prosthetics",
            "M": "Other Medical Services",
            "P": "Pathology",
            "Q": "Temporary Codes",
            "R": "Diagnostic Radiology",
            "S": "Private Payer Codes",
            "T": "State Medicaid",
            "V": "Vision/Hearing",
        }
        return categories.get(first_char, "Other")
    
    return "Other"


def download_fee_schedule() -> dict:
    """
    Download and parse Medicare Physician Fee Schedule.
    
    Returns:
        dict: Parsed fee schedule with RVUs and payment amounts
    """
    logger.info("=== Downloading Medicare Fee Schedule ===")
    
    fee_dir = DATA_DIR / "fee_schedules"
    zip_path = fee_dir / "fee_schedule.zip"
    
    # Try to download from CMS
    if download_file(CMS_URLS["fee_schedule"], zip_path):
        extract_zip(zip_path, fee_dir)
        fees = parse_fee_schedule_files(fee_dir)
        if fees:
            save_processed_data("fee_schedule.json", fees)
            return fees
    
    # Create fee schedule from sample CPT data
    logger.warning("Using sample fee schedule data (download failed)")
    fees = {
        code: {
            "code": code,
            "description": data["description"],
            "rvu": data.get("rvu", 1.0),
            "national_payment": data.get("fair_price", 100.0),
            "fair_price_low": data.get("fair_price", 100.0) * 0.6,
            "fair_price_high": data.get("fair_price", 100.0) * 1.5,
        }
        for code, data in SAMPLE_CPT_CODES.items()
    }
    save_processed_data("fee_schedule.json", fees)
    return fees


def parse_fee_schedule_files(directory: Path) -> dict:
    """
    Parse Medicare fee schedule files.
    
    Args:
        directory: Directory containing extracted files
        
    Returns:
        dict: Parsed fee data
    """
    fees = {}
    
    for data_file in list(directory.glob("*.xlsx")) + list(directory.glob("*.csv")):
        try:
            import pandas as pd
            
            if data_file.suffix == ".xlsx":
                df = pd.read_excel(data_file)
            else:
                df = pd.read_csv(data_file)
            
            # Find relevant columns
            code_col = None
            rvu_col = None
            payment_col = None
            
            for col in df.columns:
                col_lower = str(col).lower()
                if "hcpc" in col_lower or "code" in col_lower:
                    code_col = col
                elif "rvu" in col_lower or "work" in col_lower:
                    rvu_col = col
                elif "payment" in col_lower or "amount" in col_lower or "national" in col_lower:
                    payment_col = col
            
            if code_col:
                for _, row in df.iterrows():
                    code = str(row[code_col]).strip()
                    if code and code != "nan":
                        rvu = float(row[rvu_col]) if rvu_col and pd.notna(row.get(rvu_col)) else 1.0
                        payment = float(row[payment_col]) if payment_col and pd.notna(row.get(payment_col)) else 100.0
                        
                        fees[code] = {
                            "code": code,
                            "rvu": rvu,
                            "national_payment": payment,
                            "fair_price_low": payment * 0.6,
                            "fair_price_high": payment * 1.5,
                        }
            
            if fees:
                logger.info(f"Parsed {len(fees)} fee entries from {data_file.name}")
                break
                
        except Exception as e:
            logger.error(f"Error parsing {data_file}: {e}")
    
    return fees


def save_indian_rates() -> dict:
    """
    Save Indian healthcare rates (CGHS/PMJAY).
    
    Returns:
        dict: Indian rate data
    """
    logger.info("=== Saving Indian Healthcare Rates ===")
    
    # Enhanced rates with more procedures
    indian_rates = {
        "cghs": CGHS_RATES,
        "pmjay": {
            # PMJAY (Ayushman Bharat) package rates - sample
            "packages": {
                "cataract_surgery": 15000.0,
                "appendectomy": 20000.0,
                "hernia_repair": 17000.0,
                "cesarean_section": 12000.0,
                "normal_delivery": 9000.0,
                "knee_replacement": 80000.0,
                "hip_replacement": 80000.0,
                "coronary_bypass": 120000.0,
                "angioplasty_single": 50000.0,
                "dialysis_per_session": 1500.0,
            },
        },
        "nabh_rates": {
            # NABH accredited hospital typical rates
            "consultation": {
                "general": 500.0,
                "specialist": 1000.0,
            },
            "room_charges_per_day": {
                "general": 2500.0,
                "semi_private": 5000.0,
                "private": 10000.0,
                "icu": 15000.0,
            },
        },
        "currency": "INR",
        "last_updated": datetime.now().isoformat(),
    }
    
    save_processed_data("indian_rates.json", indian_rates)
    
    # Also save to dedicated directory
    indian_dir = DATA_DIR / "indian_rates"
    indian_dir.mkdir(parents=True, exist_ok=True)
    
    with open(indian_dir / "rates.json", "w") as f:
        json.dump(indian_rates, f, indent=2)
    
    logger.info("Saved Indian healthcare rates")
    return indian_rates


def save_processed_data(filename: str, data: dict) -> None:
    """
    Save processed data to JSON file.
    
    Args:
        filename: Output filename
        data: Data to save
    """
    output_path = DATA_DIR / "processed" / filename
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)
    
    logger.info(f"Saved processed data: {output_path}")


def create_combined_database() -> dict:
    """
    Create a combined database for quick lookups.
    
    Returns:
        dict: Combined code database
    """
    logger.info("=== Creating Combined Database ===")
    
    processed_dir = DATA_DIR / "processed"
    
    combined = {
        "icd10": {},
        "cpt_hcpcs": {},
        "fee_schedule": {},
        "indian_rates": {},
        "metadata": {
            "created": datetime.now().isoformat(),
            "version": "1.0",
        },
    }
    
    # Load processed files
    for data_file in processed_dir.glob("*.json"):
        try:
            with open(data_file, "r") as f:
                data = json.load(f)
            
            if "icd10" in data_file.name:
                combined["icd10"] = data
            elif "hcpcs" in data_file.name:
                combined["cpt_hcpcs"] = data
            elif "fee" in data_file.name:
                combined["fee_schedule"] = data
            elif "indian" in data_file.name:
                combined["indian_rates"] = data
                
        except Exception as e:
            logger.error(f"Error loading {data_file}: {e}")
    
    # Save combined database
    combined_path = processed_dir / "combined_codes.json"
    with open(combined_path, "w") as f:
        json.dump(combined, f, indent=2)
    
    logger.info(f"Created combined database with:")
    logger.info(f"  - {len(combined['icd10'])} ICD-10 codes")
    logger.info(f"  - {len(combined['cpt_hcpcs'])} CPT/HCPCS codes")
    logger.info(f"  - {len(combined['fee_schedule'])} fee schedule entries")
    
    return combined


def main():
    """Main entry point for downloading medical codes."""
    logger.info("=" * 60)
    logger.info("Medical Coding Data Download Script")
    logger.info("=" * 60)
    
    # Create directories
    ensure_directories()
    
    # Download and process each data source
    icd10_codes = download_icd10_codes()
    hcpcs_codes = download_hcpcs_codes()
    fee_schedule = download_fee_schedule()
    indian_rates = save_indian_rates()
    
    # Create combined database
    combined = create_combined_database()
    
    logger.info("=" * 60)
    logger.info("Download complete!")
    logger.info(f"Data saved to: {DATA_DIR}")
    logger.info("=" * 60)
    
    return combined


if __name__ == "__main__":
    main()

