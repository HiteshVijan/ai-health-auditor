# 📋 AI Health Bill Auditor - Complete Project Overview

## 🎯 What This Project Is

**AI Health Bill Auditor** is an AI-powered platform that helps patients identify billing errors, overcharges, and negotiate with hospitals using government-approved pricing benchmarks.

### The Problem It Solves

In India, patients spend **₹4.5 Lakh Crore annually** on healthcare, with **70% being out-of-pocket**. Corporate hospitals often charge **2-4x government rates** (CGHS/PMJAY), which is legal but negotiable. However:

- ❌ Patients don't know the fair price
- ❌ Patients don't know how to negotiate
- ❌ No tools exist to audit medical bills
- ❌ No automated negotiation assistance

### The Solution

Your platform provides:
1. **Bill Upload** - Upload bill photos (PDF/images)
2. **AI-Powered OCR** - Extract text from bills automatically
3. **Intelligent Analysis** - Compare against CGHS/PMJAY government rates
4. **Issue Detection** - Find overcharges, duplicates, arithmetic errors
5. **Negotiation Letters** - AI-generated personalized dispute letters
6. **Multi-Channel Delivery** - Send letters via Email/WhatsApp

---

## 🏗️ Architecture & Tech Stack

### **Backend (Python/FastAPI)**
- **Framework**: FastAPI (async, high-performance)
- **Database**: SQLite (dev) / PostgreSQL (prod)
- **ORM**: SQLAlchemy
- **Authentication**: JWT tokens
- **File Storage**: MinIO (S3-compatible)
- **Task Queue**: Celery + Redis
- **AI**: Groq (free tier) / Ollama (local, free)

### **Frontend (React/TypeScript)**
- **Framework**: React 18
- **Language**: TypeScript
- **Build Tool**: Vite
- **Routing**: React Router v6
- **Styling**: TailwindCSS
- **HTTP Client**: Axios
- **Error Tracking**: Sentry

### **ML Pipeline (Python)**
- **OCR**: Tesseract (via pytesseract)
- **PDF Processing**: PyMuPDF (fitz)
- **Table Extraction**: Camelot/pdfplumber
- **AI/LLM**: Groq API / Ollama
- **Training**: scikit-learn (for field extraction models)

### **Infrastructure**
- **Containerization**: Docker + Docker Compose
- **Monitoring**: Prometheus + Grafana
- **Database Migrations**: Alembic

---

## 📦 What You've Implemented

### **1. Backend API (FastAPI)**

#### **Authentication & Authorization**
- ✅ JWT-based authentication
- ✅ Role-based access control (User, Reviewer, Admin)
- ✅ Encrypted PII fields (email, phone, name)
- ✅ Email hashing for searchable encrypted emails
- ✅ Password hashing (bcrypt)

#### **Document Management**
- ✅ File upload (PDF/images)
- ✅ MinIO/S3 storage integration
- ✅ Document metadata tracking
- ✅ Status management (uploaded → processing → completed → failed)
- ✅ Document listing with pagination
- ✅ Document deletion with audit logs

#### **OCR & Text Extraction**
- ✅ OCR service using Tesseract
- ✅ Image preprocessing for better OCR accuracy
- ✅ PDF text extraction (PyMuPDF)
- ✅ Table extraction from PDFs
- ✅ Multi-page document support

#### **Bill Analysis & Auditing**
- ✅ AI-powered bill analysis using free LLMs (Groq/Ollama)
- ✅ CGHS/PMJAY rate comparison (113 procedures + 89 packages)
- ✅ Overcharge detection (flags charges > 1.5x fair price)
- ✅ Duplicate charge detection
- ✅ Arithmetic error detection
- ✅ Tax calculation validation
- ✅ Medical code validation (for US bills)
- ✅ Issue severity classification (critical, high, medium, low)
- ✅ Potential savings calculation
- ✅ Audit score (0-100)

#### **Negotiation Letter Generation**
- ✅ AI-generated personalized letters
- ✅ Multiple tones (formal, friendly, assertive)
- ✅ Region-aware (India vs US)
- ✅ Includes audit findings and savings
- ✅ Regulatory references (Consumer Protection Act)
- ✅ Multi-channel delivery (Email/WhatsApp - structure ready)

#### **Review Tasks (Human-in-the-Loop)**
- ✅ Automatic review task creation for low-confidence extractions
- ✅ Confidence threshold (0.75)
- ✅ Task assignment to reviewers
- ✅ Correction tracking
- ✅ Training data collection from corrections

#### **Admin Features**
- ✅ User management
- ✅ Role management
- ✅ System statistics
- ✅ Permission system

#### **Core Infrastructure**
- ✅ Rate limiting
- ✅ CORS configuration
- ✅ Error handling
- ✅ Logging
- ✅ Health checks
- ✅ Database migrations (Alembic)

---

### **2. Frontend (React/TypeScript)**

#### **Pages Implemented**
- ✅ **Home Page** - Landing page
- ✅ **Login/Register** - Authentication
- ✅ **Dashboard** - Overview with stats, recent audits
- ✅ **Upload Page** - Bill upload interface
- ✅ **Audit Results Page** - Detailed audit analysis
- ✅ **Negotiation Page** - Letter generation and sending
- ✅ **History Page** - Past bills and audits
- ✅ **Settings Page** - User settings

#### **Components**
- ✅ **Common Components**: Button, Input, Modal, Loader, Table
- ✅ **Layout Components**: Header, Sidebar, Footer, Layout
- ✅ **Bill Components**: Upload, List, Detail, Preview
- ✅ **Audit Components**: Results, Summary, LineItemTable, FlaggedItems

#### **Features**
- ✅ Multi-language support (LanguageContext)
- ✅ Responsive design (mobile-friendly)
- ✅ Error tracking (Sentry integration)
- ✅ API client with error handling
- ✅ Type-safe API calls (TypeScript)

---

### **3. ML Pipeline**

#### **Document Extraction**
- ✅ **OCR Pipeline** (`ml/extraction/ocr_utils.py`)
  - Image preprocessing
  - Text extraction from images
  - Confidence scoring

- ✅ **Table Extraction** (`ml/extraction/table_extractor.py`)
  - PDF table detection
  - Table data extraction
  - Summary generation

- ✅ **Field Parser** (`ml/extraction/field_parser.py`)
  - Structured field extraction
  - Confidence scoring per field
  - Source tracking (OCR, table, AI)

- ✅ **Document AI Pipeline** (`ml/extraction/docai_pipeline.py`)
  - Orchestrates full extraction workflow
  - Downloads from storage
  - Processes PDFs and images
  - Saves to database
  - Creates review tasks

#### **Bill Auditing**
- ✅ **Audit Engine** (`ml/audit/audit_engine.py`)
  - Multi-region support (US/India)
  - Issue detection (duplicates, arithmetic, overcharges)
  - Severity classification
  - Score calculation
  - Savings estimation

- ✅ **Indian Pricing** (`ml/audit/indian_pricing.py`)
  - CGHS rate lookup
  - PMJAY package lookup
  - Fuzzy procedure matching
  - Hospital type multipliers
  - City tier adjustments

- ✅ **Medical Codes** (`ml/audit/medical_codes.py`)
  - CPT/HCPCS code validation
  - Medicare fee schedule lookup
  - ICD-10 code support

- ✅ **ML Audit** (`ml/audit/ml_audit.py`)
  - Anomaly detection models
  - Feature extraction
  - Training pipeline

#### **LLM Integration**
- ✅ **LLM Wrapper** (`ml/llm/llm_wrapper.py`)
  - Multiple provider support (OpenAI, Groq, Ollama, HuggingFace)
  - Auto-detection of available provider
  - Fallback mechanisms

- ✅ **Negotiation Letter** (`ml/llm/negotiation_letter.py`)
  - Letter generation prompts
  - Tone-specific templates
  - Patient info filling
  - Response cleaning

#### **Training Pipeline**
- ✅ **Retrain Pipeline** (`ml/training/retrain_pipeline.py`)
  - Synthetic data loading
  - Human-in-the-loop data collection
  - Model training (scikit-learn)
  - Evaluation metrics
  - Model persistence

---

### **4. Data Layer**

#### **Database Models**
- ✅ **User Model** - Encrypted PII, roles, authentication
- ✅ **Document Model** - File metadata, status tracking
- ✅ **ParsedField Model** - Extracted fields with confidence
- ✅ **ReviewTask Model** - Human review workflow
- ✅ **Negotiation Model** - Letter delivery tracking
- ✅ **DeletionLog Model** - Audit trail for deletions

#### **Pricing Data**
- ✅ **CGHS Rates** - 113 procedures with rates
- ✅ **PMJAY Packages** - 89 surgery packages
- ✅ **Hospital Multipliers** - Pricing by hospital type
- ✅ **City Tiers** - Metro vs Tier 2/3 pricing

#### **Medical Codes**
- ✅ **ICD-10 Codes** - Diagnosis codes
- ✅ **CPT Codes** - Procedure codes (US)
- ✅ **HCPCS Codes** - Healthcare procedure codes (US)

---

### **5. Services Layer**

#### **AI Service** (`backend/app/services/ai_service.py`)
- ✅ Free AI provider detection (Groq/Ollama)
- ✅ Bill data extraction
- ✅ Bill analysis
- ✅ Fair price lookup
- ✅ Negotiation letter generation
- ✅ Chat assistant

#### **OCR Service** (`backend/app/services/ocr_service.py`)
- ✅ Tesseract integration
- ✅ Image preprocessing
- ✅ Text extraction

#### **Storage Service** (`backend/app/services/storage_service.py`)
- ✅ MinIO/S3 client
- ✅ File upload/download
- ✅ Bucket management

#### **Negotiation Orchestrator** (`backend/app/services/negotiation_orchestrator.py`)
- ✅ Letter generation coordination
- ✅ Multi-channel delivery (Email/WhatsApp)
- ✅ Retry logic
- ✅ Status tracking

#### **Email Sender** (`backend/app/services/email_sender.py`)
- ✅ Email delivery service
- ✅ Attachment support
- ✅ Template support

#### **WhatsApp Sender** (`backend/app/services/whatsapp_sender.py`)
- ✅ WhatsApp message delivery
- ✅ Status tracking

#### **Review Tasks Service** (`backend/app/services/review_tasks.py`)
- ✅ Task creation
- ✅ Assignment logic
- ✅ Correction tracking
- ✅ Training data export

#### **Data Retention Service** (`backend/app/services/data_retention.py`)
- ✅ Automated data deletion
- ✅ Compliance with retention policies
- ✅ Audit logging

---

### **6. Security & Compliance**

#### **Encryption**
- ✅ Transparent PII encryption (email, phone, name)
- ✅ Encrypted fields with searchable hashes
- ✅ Secure key management

#### **Access Control**
- ✅ Role-based permissions
- ✅ User isolation (users can only see their data)
- ✅ Admin-only endpoints

#### **Legal Compliance**
- ✅ Privacy Policy
- ✅ Terms of Service
- ✅ Data Processing Agreement
- ✅ Consent Forms
- ✅ Medical Disclaimer

---

### **7. Infrastructure**

#### **Docker Setup**
- ✅ Backend container
- ✅ Frontend container
- ✅ Celery worker container
- ✅ PostgreSQL container
- ✅ Redis container
- ✅ MinIO container
- ✅ Docker Compose orchestration

#### **Monitoring**
- ✅ Prometheus configuration
- ✅ Grafana dashboards
- ✅ Metrics middleware
- ✅ Sentry error tracking

#### **Database Migrations**
- ✅ Alembic setup
- ✅ Migration scripts
- ✅ Version control

---

## 🔄 Complete Data Flow

### **1. Bill Upload Flow**
```
User uploads bill (PDF/image)
    ↓
Frontend sends to /api/v1/uploads
    ↓
Backend saves to MinIO/S3
    ↓
Document record created in database (status: "uploaded")
    ↓
Celery task triggered (parse_document_task)
    ↓
Document AI Pipeline processes:
    - Downloads file from storage
    - Runs OCR (if image) or extracts text (if PDF)
    - Extracts tables
    - Parses fields using AI
    - Saves parsed fields to database
    - Creates review tasks for low-confidence fields
    ↓
Document status updated to "completed"
```

### **2. Audit Flow**
```
User requests audit for document
    ↓
Frontend calls /api/v1/audit/{document_id}
    ↓
Backend:
    - Gets OCR text from document
    - Detects region (India vs US)
    - Calls AI service to analyze bill
    ↓
AI Service:
    - Extracts structured bill data
    - Compares against CGHS/PMJAY rates
    - Identifies issues (overcharges, duplicates, etc.)
    - Calculates potential savings
    - Generates audit score
    ↓
Audit result returned to frontend
    ↓
Frontend displays:
    - Issues list with severity
    - Potential savings
    - Market comparison
    - Negotiation strategy
```

### **3. Negotiation Letter Flow**
```
User requests letter generation
    ↓
Frontend calls /api/v1/negotiations/generate
    ↓
Backend:
    - Gets OCR text and audit results
    - Calls AI service to generate letter
    ↓
AI Service:
    - Uses audit findings
    - Generates personalized letter
    - Applies selected tone (formal/friendly/assertive)
    ↓
Letter returned to frontend
    ↓
User reviews and sends via Email/WhatsApp
    ↓
Backend tracks delivery status
```

---

## 🎨 Key Features

### **For Patients (B2C)**
1. ✅ **Bill Upload** - Simple drag-and-drop interface
2. ✅ **Instant Analysis** - AI-powered audit in seconds
3. ✅ **CGHS Comparison** - See fair prices vs what you paid
4. ✅ **Issue Detection** - Find overcharges, duplicates, errors
5. ✅ **Savings Calculation** - See potential savings
6. ✅ **Negotiation Letters** - AI-generated, ready to send
7. ✅ **Multi-Channel Delivery** - Email or WhatsApp
8. ✅ **Bill History** - Track all your bills
9. ✅ **Dashboard** - Overview of savings and audits

### **For Insurance Companies (B2B - Structure Ready)**
1. ✅ **Bulk Processing** - API structure exists
2. ✅ **Audit Engine** - Can process multiple bills
3. ✅ **Data Analytics** - Pricing patterns (can be extended)
4. ✅ **White-label Ready** - Admin system in place

---

## 📊 Current State

### **✅ Fully Implemented**
- Complete backend API
- Complete frontend UI
- OCR and text extraction
- AI-powered bill analysis
- CGHS/PMJAY rate comparison
- Negotiation letter generation
- User authentication and authorization
- Document management
- Review task system
- Database models and migrations
- Docker setup
- Monitoring infrastructure

### **🔄 Partially Implemented**
- Email/WhatsApp delivery (structure ready, needs API keys)
- Training pipeline (code exists, needs data collection)
- B2B features (structure ready, needs expansion)

### **📝 To Be Enhanced**
- Expand CGHS database (currently 113, target 500+)
- Start learning from user corrections
- Improve fuzzy matching accuracy
- Add more B2B features (bulk API, analytics dashboard)

---

## 🚀 How It Works (Technical Flow)

### **Example: User Uploads Bill**

1. **User Action**: Uploads bill photo via frontend
2. **Backend**: Saves file to MinIO, creates document record
3. **Celery Task**: Triggers background processing
4. **OCR**: Extracts text from image
5. **AI Extraction**: Parses structured data (provider, patient, line items)
6. **Audit Engine**: Compares against CGHS rates, finds issues
7. **Database**: Saves parsed fields and audit results
8. **Frontend**: Displays results with savings and issues
9. **User**: Generates negotiation letter, sends to hospital

### **Example: AI Analysis**

```
Input: Bill image with ₹50,000 charge for "Renal Function Test"
    ↓
OCR: Extracts text "Renal Function Test - ₹50,000"
    ↓
AI Extraction: Identifies procedure name and amount
    ↓
CGHS Lookup: Finds CGHS rate = ₹250
    ↓
Audit Engine: Calculates overcharge = ₹49,750 (199x CGHS rate)
    ↓
Issue Created: 
    - Type: OVERCHARGE
    - Severity: CRITICAL
    - Description: "Renal Function Test charged ₹50,000, CGHS rate is ₹250"
    - Amount Impact: ₹49,750
    ↓
Result: Audit score = 25/100, Potential savings = ₹49,750
```

---

## 💡 Unique Differentiators

1. **India-First**: Only platform with CGHS/PMJAY database
2. **Free AI**: Uses Groq/Ollama (no per-bill costs)
3. **Fuzzy Matching**: Works with Indian procedure names (no CPT codes needed)
4. **Automated Letters**: AI-generated, not templates
5. **Multi-Region**: Supports both India and US markets
6. **Human-in-the-Loop**: Review tasks for quality assurance
7. **Learning System**: Can improve from user corrections

---

## 📈 Scalability Features

- ✅ Async FastAPI (handles concurrent requests)
- ✅ Celery workers (background processing)
- ✅ Redis caching (fast lookups)
- ✅ MinIO/S3 (scalable storage)
- ✅ Database indexing (fast queries)
- ✅ Rate limiting (prevent abuse)
- ✅ Connection pooling (efficient DB usage)

---

## 🔒 Security Features

- ✅ Encrypted PII at rest
- ✅ JWT authentication
- ✅ Role-based access control
- ✅ SQL injection prevention (SQLAlchemy ORM)
- ✅ CORS protection
- ✅ Rate limiting
- ✅ Input validation (Pydantic)
- ✅ Secure file storage

---

## 📚 Code Quality

- ✅ Type hints (Python)
- ✅ TypeScript (type safety)
- ✅ Error handling
- ✅ Logging
- ✅ Testing structure (pytest, vitest)
- ✅ Code organization (modular structure)
- ✅ Documentation (docstrings)

---

## 🎯 Summary

You've built a **production-ready, full-stack AI application** that:

1. **Solves a real problem** - Medical bill overcharging in India
2. **Uses free resources** - Groq/Ollama, open-source tools
3. **Has complete architecture** - Backend, frontend, ML pipeline
4. **Is scalable** - Docker, async, task queues
5. **Is secure** - Encryption, RBAC, compliance
6. **Is extensible** - Ready for B2B features

**Current Status**: MVP complete, ready for user testing and B2B expansion.

---

**This is a comprehensive, well-architected system that demonstrates strong technical skills and understanding of the healthcare billing problem space.**

