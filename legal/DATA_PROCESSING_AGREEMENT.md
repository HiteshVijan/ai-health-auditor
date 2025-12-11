# Data Processing Agreement

**Between {{COMPANY_NAME}} and Data Principal**

**Version: {{VERSION}}**  
**Effective Date: {{EFFECTIVE_DATE}}**

---

## 1. Introduction

This Data Processing Agreement ("**DPA**") forms part of the Terms of Service between {{COMPANY_NAME}} ("**Data Fiduciary**" or "**Processor**") and you ("**Data Principal**" or "**Controller**") for the AI Health Bill Auditor service.

This DPA is designed to comply with the **Digital Personal Data Protection Act, 2023 (DPDPA)** of India and align with international standards including **GDPR**.

---

## 2. Definitions

| Term | Definition |
|------|------------|
| **Personal Data** | Any data about an individual who is identifiable by or in relation to such data |
| **Sensitive Personal Data (SPDI)** | Personal data relating to health, finances, passwords, biometrics as defined under applicable law |
| **Health Data** | Personal data relating to physical or mental health, including medical records and billing |
| **Processing** | Any operation on personal data including collection, storage, use, disclosure, and deletion |
| **Data Fiduciary** | {{COMPANY_NAME}}, which determines purpose and means of processing |
| **Data Processor** | Entity that processes data on behalf of the Data Fiduciary |
| **Data Principal** | The individual whose personal data is being processed |

---

## 3. Scope of Processing

### 3.1 Categories of Data Processed

| Category | Examples | Sensitivity Level |
|----------|----------|-------------------|
| Identity Data | Name, date of birth | Personal Data |
| Contact Data | Email, phone, address | Personal Data |
| Health Data | Diagnoses, procedures, medications | SPDI / Health Data |
| Financial Data | Bill amounts, insurance info | SPDI |
| Document Data | Uploaded bills, invoices | Contains SPDI |

### 3.2 Purposes of Processing

| Purpose | Legal Basis | Retention |
|---------|-------------|-----------|
| Document analysis and OCR | Consent / Contract | 90 days |
| Billing error detection | Consent | 1 year |
| Audit report generation | Consent | 7 years |
| Negotiation letter creation | Explicit Consent | 1 year |
| Service improvement | Legitimate Interest | Anonymized |

### 3.3 Processing Activities

- Collection via secure upload
- Storage in encrypted databases
- Automated analysis using AI/ML
- Human review for quality assurance
- Generation of reports and summaries
- Secure deletion upon request or retention expiry

---

## 4. Data Fiduciary Obligations

{{COMPANY_NAME}} shall:

### 4.1 Lawful Processing
- Process data only for specified, lawful purposes
- Obtain and document valid consent
- Process data in accordance with applicable law

### 4.2 Security Measures
- Implement appropriate technical measures:
  - AES-256 encryption at rest
  - TLS 1.3 encryption in transit
  - Role-based access controls
  - Multi-factor authentication
  - Regular security audits

- Implement appropriate organizational measures:
  - Employee training
  - Background checks
  - Confidentiality agreements
  - Access logging

### 4.3 Data Principal Rights
- Facilitate exercise of rights under DPDPA
- Respond to requests within 30 days
- Provide data access summaries
- Enable correction and deletion

### 4.4 Breach Notification
- Notify Data Protection Board within 72 hours of a breach
- Notify affected Data Principals without undue delay
- Document breaches and remediation

### 4.5 Sub-Processors
- Engage sub-processors only with appropriate agreements
- Maintain list of sub-processors (see Appendix A)
- Ensure sub-processors meet security standards

---

## 5. Data Principal Rights

You have the right to:

| Right | Description | Method |
|-------|-------------|--------|
| Access | Obtain summary of your data | Dashboard / DPO request |
| Correction | Request correction of inaccurate data | Dashboard / DPO request |
| Erasure | Request deletion of your data | API / Dashboard / DPO request |
| Portability | Receive data in machine-readable format | Export feature |
| Withdraw Consent | Revoke consent at any time | Dashboard / DPO request |
| Grievance | Lodge complaints | Grievance Officer |

---

## 6. Data Transfers

### 6.1 Primary Location
Data is primarily processed in **{{DATA_CENTER_LOCATION}}**.

### 6.2 International Transfers
If data is transferred outside India:
- Only to countries with adequate protection, OR
- With Standard Contractual Clauses, OR
- With your explicit consent

### 6.3 Sub-Processors
Current sub-processors:

| Provider | Purpose | Location | Safeguards |
|----------|---------|----------|------------|
| {{CLOUD_PROVIDER}} | Infrastructure | {{CLOUD_LOCATION}} | DPA, Encryption |
| {{STORAGE_PROVIDER}} | Object Storage | {{STORAGE_LOCATION}} | DPA, Encryption |
| {{AI_PROVIDER}} | AI Processing | {{AI_LOCATION}} | DPA, Anonymization |

---

## 7. Data Retention

### 7.1 Retention Schedule

| Data Type | Retention Period | Post-Retention Action |
|-----------|------------------|----------------------|
| Account Data | Account lifetime + 3 years | Deletion |
| Uploaded Documents | 90 days after processing | Secure deletion |
| Audit Reports | 7 years | Deletion |
| Parsed Data | 1 year or on request | Deletion |
| Audit Logs | Permanent | Anonymization |

### 7.2 Deletion Process
- Secure deletion from primary storage
- Removal from backups within 90 days
- Verification of deletion
- Audit log retention

---

## 8. Security Incident Response

### 8.1 Incident Classification

| Severity | Definition | Response Time |
|----------|------------|---------------|
| Critical | Active breach, data exfiltration | Immediate |
| High | Vulnerability exploited | 4 hours |
| Medium | Potential vulnerability | 24 hours |
| Low | Minor security event | 72 hours |

### 8.2 Notification Timeline
- **72 hours**: Notify Data Protection Board (if required)
- **Without undue delay**: Notify affected Data Principals
- **Ongoing**: Status updates until resolution

---

## 9. Audit Rights

### 9.1 Your Rights
You may request:
- Information about security measures
- Compliance certifications
- Third-party audit reports

### 9.2 Our Certifications
{{COMPANY_NAME}} maintains:
- ISO 27001 (or target certification)
- SOC 2 Type II (or target certification)
- Regular penetration testing

---

## 10. Liability

### 10.1 Data Fiduciary Liability
{{COMPANY_NAME}} is liable for:
- Breaches caused by our negligence
- Failure to implement required security measures
- Violations of this DPA

### 10.2 Limitations
Liability is limited as specified in the Terms of Service, except where prohibited by law.

---

## 11. Term and Termination

### 11.1 Duration
This DPA is effective from acceptance and continues until:
- Termination of your account
- Mutual agreement
- Expiry of data retention periods

### 11.2 Post-Termination
Upon termination:
- Processing ceases (except for legal retention)
- Data is deleted per retention schedule
- Deletion confirmation provided upon request

---

## 12. Amendments

This DPA may be amended:
- With 30 days notice for material changes
- Immediately for legal compliance
- With your consent for other changes

---

## 13. Contact

**Data Protection Officer:**  
{{DPO_NAME}}  
{{DPO_EMAIL}}  
{{DPO_PHONE}}

**Grievance Officer:**  
{{GRIEVANCE_OFFICER_NAME}}  
{{GRIEVANCE_EMAIL}}

---

## Appendix A: Sub-Processor List

| Sub-Processor | Service | Location | DPA Status |
|---------------|---------|----------|------------|
| {{SUB_PROCESSOR_1}} | {{SERVICE_1}} | {{LOCATION_1}} | Signed |
| {{SUB_PROCESSOR_2}} | {{SERVICE_2}} | {{LOCATION_2}} | Signed |
| {{SUB_PROCESSOR_3}} | {{SERVICE_3}} | {{LOCATION_3}} | Signed |

*Updated: {{SUB_PROCESSOR_UPDATE_DATE}}*

---

## Appendix B: Technical Security Measures

### Encryption
- At Rest: AES-256
- In Transit: TLS 1.3
- Key Management: {{KMS_PROVIDER}}

### Access Control
- Authentication: JWT + MFA
- Authorization: RBAC
- Session Management: Secure, time-limited tokens

### Monitoring
- Logging: All access logged
- Alerting: Real-time security alerts
- Retention: 1 year

### Physical Security
- Data Center: {{DATA_CENTER_TIER}}
- Access: Biometric + card
- Surveillance: 24/7

---

*This document is a template and should be reviewed by qualified legal counsel before use.*

---

**Placeholders to Replace:**
- `{{COMPANY_NAME}}` - Your company's legal name
- `{{VERSION}}` - Document version (e.g., "1.0")
- `{{EFFECTIVE_DATE}}` - Agreement effective date
- `{{DATA_CENTER_LOCATION}}` - Primary data center location
- `{{CLOUD_PROVIDER}}` - Cloud infrastructure provider
- `{{CLOUD_LOCATION}}` - Cloud provider location
- `{{STORAGE_PROVIDER}}` - Object storage provider
- `{{STORAGE_LOCATION}}` - Storage provider location
- `{{AI_PROVIDER}}` - AI/ML service provider
- `{{AI_LOCATION}}` - AI provider location
- `{{DPO_NAME}}` - Data Protection Officer name
- `{{DPO_EMAIL}}` - DPO email
- `{{DPO_PHONE}}` - DPO phone
- `{{GRIEVANCE_OFFICER_NAME}}` - Grievance Officer name
- `{{GRIEVANCE_EMAIL}}` - Grievance email
- `{{SUB_PROCESSOR_1}}`, etc. - Sub-processor names
- `{{SERVICE_1}}`, etc. - Sub-processor services
- `{{LOCATION_1}}`, etc. - Sub-processor locations
- `{{SUB_PROCESSOR_UPDATE_DATE}}` - Last update date
- `{{KMS_PROVIDER}}` - Key management service
- `{{DATA_CENTER_TIER}}` - Data center tier level

