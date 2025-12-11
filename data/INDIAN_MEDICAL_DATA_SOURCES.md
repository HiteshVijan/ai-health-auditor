# 🇮🇳 FREE Indian Medical Bill Data Sources

## For Training AI Models on Indian Healthcare Pricing

### 1. **CGHS Rate Lists (Central Government Health Scheme)**
- **Source**: https://cghs.gov.in/
- **Data**: Official rates for 1,700+ procedures
- **Format**: PDF, can be parsed to JSON
- **Coverage**: All major treatments, tests, surgeries
- **Use**: Benchmark for "fair pricing"

### 2. **PMJAY/Ayushman Bharat Package Rates**
- **Source**: https://pmjay.gov.in/
- **Data**: 1,500+ treatment packages with fixed rates
- **Coverage**: Surgeries, medical treatments, daycare
- **Use**: Insurance benchmark pricing

### 3. **State Government ESIS Rates**
- **Source**: esic.nic.in (Employees' State Insurance)
- **Data**: Approved rates for empaneled hospitals
- **Coverage**: All states have their own rate lists

### 4. **NABL Lab Test Rates**
- Common diagnostic test pricing
- Renal Function Test: ₹200-400 (CGHS: ₹250)
- Tacrolimus Level: ₹600-1000 (CGHS: ₹800)
- Complete Blood Count: ₹150-300
- Lipid Profile: ₹200-400

### 5. **Hospital Chain Published Rates**
Some hospitals publish rate cards:
- Apollo: Rate card for common procedures
- Medanta: Transparent pricing for packages
- Max Healthcare: Published surgery costs

---

## Sample CGHS Rates (For Your Medanta Bill)

| Test/Procedure | CGHS Rate | Typical Private | Your Bill |
|---------------|-----------|-----------------|-----------|
| Renal Function Test | ₹250 | ₹500-1000 | ₹990 |
| Tacrolimus Level | ₹800 | ₹1500-2500 | ₹2390 |
| Consultation | ₹150-500 | ₹500-1500 | ₹0 (waived) |

**Your Medanta Bill Analysis:**
- Total Paid: ₹3,380
- CGHS Equivalent: ₹1,050
- Overcharge: ₹2,330 (222% above CGHS)
- This is NORMAL for corporate hospitals - they charge 2-4x CGHS

---

## Data We Already Have

Located in `/data/indian_rates/`:

1. **cghs_rates.json** - 113 procedures with CGHS pricing
2. **pmjay_packages.json** - 89 surgery packages
3. **hospital_multipliers.json** - Pricing by hospital type
4. **city_tiers.json** - Metro vs Tier 2/3 pricing

---

## How to Improve AI Training

### Option 1: Fine-tune on CGHS Data (Free)
```python
# Use our existing CGHS data to teach the model
training_examples = [
    {
        "bill": "Renal Function Test - ₹990",
        "analysis": "Overcharged. CGHS rate is ₹250. Corporate hospital markup of 296%"
    },
    ...
]
```

### Option 2: Synthetic Bill Generation
Generate realistic bills using our pricing database:
- Random hospital types
- Random procedures from CGHS list
- Apply realistic markups
- Create training pairs (bill → issues)

### Option 3: Collect Real Bills (with consent)
- Partner with patient advocacy groups
- Anonymize and use for training
- Build a community-contributed dataset

---

## Regulatory References for AI

The AI should know these Indian healthcare regulations:

1. **Clinical Establishments Act, 2010** - Rate transparency
2. **Consumer Protection Act, 2019** - Patient rights
3. **RTI Act, 2005** - Right to information
4. **IRDAI Guidelines** - Insurance claim standards
5. **NMC (National Medical Commission)** - Doctor fee guidelines

---

## Next Steps for Your Product

1. ✅ We have CGHS/PMJAY data loaded
2. ✅ AI detects Indian vs US bills
3. 🔄 Add OCR to extract text from bill images
4. 🔄 Fine-tune AI on Indian medical terminology
5. 🔄 Build a bill submission + feedback loop for training

