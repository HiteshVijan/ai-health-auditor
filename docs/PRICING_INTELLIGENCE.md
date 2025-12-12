# 📊 Pricing Intelligence Module

## Overview

Clean, simple architecture for healthcare pricing intelligence:

1. **Official Rates** - Loaded directly from JSON files (CGHS/PMJAY)
2. **Crowdsourced Data** - Collected from user bills, stored in database
3. **Hospital Scoring** - Calculated from collected price data

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  PRICING INTELLIGENCE                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  DATA SOURCES:                                               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  JSON Files (Official Rates)                           │ │
│  │  • data/indian_rates/cghs_rates_2024.json              │ │
│  │  • data/indian_rates/pmjay_packages_2024.json          │ │
│  └────────────────────────────────────────────────────────┘ │
│                          +                                   │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Database (Crowdsourced)                               │ │
│  │  • hospitals - Hospital profiles                       │ │
│  │  • procedures - Procedure catalog                      │ │
│  │  • price_points - User-contributed prices              │ │
│  └────────────────────────────────────────────────────────┘ │
│                          ↓                                   │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Pricing Service                                       │ │
│  │  • Fuzzy matching for procedure names                  │ │
│  │  • Combines official + crowdsourced data               │ │
│  │  • Hospital scoring algorithm                          │ │
│  └────────────────────────────────────────────────────────┘ │
│                          ↓                                   │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  REST API                                              │ │
│  │  • /pricing/lookup - Price lookup                      │ │
│  │  • /pricing/search - Procedure search                  │ │
│  │  • /pricing/hospitals/* - Hospital endpoints           │ │
│  │  • /pricing/contribute - Crowdsource data              │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 📁 Files

### Data Files
| File | Description |
|------|-------------|
| `data/indian_rates/cghs_rates_2024.json` | Official CGHS rates |
| `data/indian_rates/pmjay_packages_2024.json` | Official PMJAY packages |

### Code Files
| File | Description |
|------|-------------|
| `backend/app/models/pricing.py` | Database models |
| `backend/app/schemas/pricing.py` | API schemas |
| `backend/app/services/pricing_service.py` | Business logic |
| `backend/app/api/v1/endpoints/pricing.py` | REST endpoints |

---

## 🔌 API Endpoints

### Price Lookup (Public)
```bash
GET /api/v1/pricing/lookup?procedure=knee+replacement
```

Response:
```json
{
  "procedure_name": "knee replacement",
  "matched_procedure": "Total Knee Replacement (one knee)",
  "match_confidence": 0.95,
  "category": "orthopedics",
  "benchmarks": [
    {"source": "CGHS", "rate": 150000},
    {"source": "PMJAY", "rate": 80000}
  ],
  "market_prices": [],
  "fair_price_range": {"low": 80000, "median": 215000, "high": 350000}
}
```

### Procedure Search
```bash
GET /api/v1/pricing/search?query=heart+surgery
```

### Hospital Search
```bash
GET /api/v1/pricing/hospitals/search?city=delhi
```

### Contribute Price (Auth Optional)
```bash
POST /api/v1/pricing/contribute
{
  "procedure_name": "MRI Brain",
  "charged_amount": 8500,
  "hospital_name": "Max Hospital",
  "city": "Delhi"
}
```

### Database Stats
```bash
GET /api/v1/pricing/stats
```

---

## 🔄 Data Flow

### User Bill → Crowdsourced Database

```
1. User uploads bill
2. OCR + AI analysis (existing flow)
3. Line items extracted
4. pricing_service.process_bill_for_pricing()
   - Creates/finds procedure in DB
   - Creates/finds hospital in DB
   - Adds price point with comparisons
5. Database grows with each bill
```

---

## 🏥 Hospital Scoring

Hospitals are scored based on crowdsourced data:

```
Pricing Score (60%):     100 - (avg_overcharge / 3)
Transparency Score (40%): Based on pricing consistency
Overall Score:           Weighted average
```

Requires minimum 3 price points to calculate score.

---

## 🚀 Quick Start

```bash
# Start backend
cd backend
USE_SQLITE=1 python run_local.py

# Test price lookup
curl "http://localhost:8000/api/v1/pricing/lookup?procedure=appendectomy"

# Test procedure search
curl "http://localhost:8000/api/v1/pricing/search?query=knee"

# Get stats
curl "http://localhost:8000/api/v1/pricing/stats"
```

---

## 📊 Data Coverage

From JSON files:
- **CGHS**: ~113 procedures with rates
- **PMJAY**: ~89 packages with rates

From crowdsourced (grows with usage):
- Hospitals: Added as bills are processed
- Price points: Added from each bill's line items
