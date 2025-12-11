# Medical Coding Data Directory

This directory contains medical coding reference data downloaded from free public sources.

## Data Sources

### 1. ICD-10-CM Codes (Diagnosis Codes)
- **Source**: CMS (Centers for Medicare & Medicaid Services)
- **URL**: https://www.cms.gov/medicare/coding-billing/icd-10-codes
- **License**: Public Domain (US Government)

### 2. HCPCS/CPT Codes (Procedure Codes)
- **Source**: CMS HCPCS Files
- **URL**: https://www.cms.gov/medicare/coding-billing/healthcare-common-procedure-system
- **License**: Public Domain (US Government)

### 3. Medicare Physician Fee Schedule
- **Source**: CMS Physician Fee Schedule
- **URL**: https://www.cms.gov/medicare/payment/fee-schedules
- **License**: Public Domain (US Government)

### 4. Indian Healthcare Rates
- **CGHS Rates**: https://cghs.gov.in/
- **PMJAY Rates**: https://pmjay.gov.in/

## Directory Structure

```
data/
├── icd10/           # ICD-10-CM diagnosis codes
├── hcpcs/           # HCPCS procedure codes
├── cpt/             # CPT code mappings
├── fee_schedules/   # Medicare & fair pricing benchmarks
├── indian_rates/    # CGHS, PMJAY rates
└── processed/       # Processed/indexed data files
```

## Setup

Run the data loader to download and process the data:

```bash
cd /path/to/AI\ Health
python -m scripts.download_medical_codes
```

## Data Update Schedule

- ICD-10 codes are updated annually (October 1)
- HCPCS codes are updated quarterly
- Fee schedules are updated annually

Last updated: [Run download script to populate]

