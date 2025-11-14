# AI-Powered Regulatory Compliance Checker for Contracts

Automatically analyze contracts for GDPR, HIPAA, CCPA, and SOX compliance using AI.  
Includes clause extraction, risk scoring, real-time alerts, and multi-platform integration.

---

## 🚀 Quick Start

### 1. Install Python 3.9+

### 2. Clone & Setup
```bash
git clone https://github.com/coder-adi6/AI-Powered-Regulatory-Compliance-Checker-for-Contracts.git
cd AI-Powered-Regulatory-Compliance-Checker-for-Contracts

python -m venv .venv
.venv\Scripts\Activate.ps1  # Windows
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

### 3. Configure API Key
Create `.env` file:
```
GROQ_API_KEY=your_groq_api_key_here
```

Get free key: https://console.groq.com/keys

### 4. Run
```bash
streamlit run app.py
```

Open browser: http://localhost:8501

---

## ✨ Features

### 🔍 AI Contract Analysis
- Extracts important clauses  
- Detects GDPR/CCPA/HIPAA/SOX violations  
- Identifies missing or weak legal terms  
- Highlights high-risk sections  

### 🛡️ Regulations Supported
- GDPR – 176 mapped requirements  
- HIPAA  
- CCPA  
- SOX  

### 📊 Risk Assessment Engine
- AI-based risk scoring  
- Low/Medium/High severity  
- Explains each risk found  

### 📤 Export Options
- PDF  
- CSV  
- JSON  

### 🔗 Integrations
- Google Sheets  
- Slack Alerts  
- Email/SMS (optional)  

### 📁 File Support
- PDF  
- DOCX  
- TXT  

---

## 🧠 How It Works

### 1. Upload Contract  
PDF/DOCX/TXT supported.

### 2. Clause Extraction  
Extracts:  
- Confidentiality  
- Data Processing  
- Liability  
- Consent  
- User Rights  

### 3. Compliance Mapping  
Cross-checks contract against:  
- GDPR articles  
- HIPAA rules  
- CCPA obligations  
- SOX controls  

### 4. Risk Scoring  
Uses LLM to rate:  
- Severity  
- Impact  
- Likelihood  

### 5. Dashboard Output  
Shows:  
- Compliance percentage  
- Violations list  
- Risk heatmap  
- Recommendations  

### 6. Export & Notify  
- Generate downloadable reports  
- Push data to Google Sheets  
- Send Slack alerts  

---

## 📐 System Architecture

```
        ┌──────────────────────────┐
        │   User Uploads Contract  │
        └──────────────┬───────────┘
                        │
                        ▼
        ┌──────────────────────────┐
        │ Preprocessing (NLP/OCR)  │
        └──────────────┬───────────┘
                        │
                        ▼
        ┌──────────────────────────┐
        │ Clause Extraction (LLM)  │
        └──────────────┬───────────┘
                        │
                        ▼
        ┌──────────────────────────────┐
        │ Compliance Mapping Engine    │
        │ (GDPR / HIPAA / CCPA / SOX) │
        └──────────────┬──────────────┘
                        │
                        ▼
        ┌──────────────────────────┐
        │ Risk Assessment Engine   │
        └──────────────┬───────────┘
                        │
                        ▼
        ┌──────────────────────────┐
        │ Streamlit Dashboard      │
        └──────────────┬───────────┘
                        │
                        ▼
        ┌──────────────────────────┐
        │ Export / Notifications   │
        └──────────────────────────┘
```

---

## 🧪 Testing Notification System
Send test alert:
```bash
python send_test_alert.py
```

Supports:
- Slack  
- Email (if enabled)  
- Google Sheets  

---

## 📦 Requirements
- Python 3.9+  
- spaCy  
- Streamlit  
- Groq API Key  
- 4GB RAM  

---

## 🛠️ Tech Stack
- Python  
- Streamlit  
- Groq API  
- spaCy NLP  
- PyPDF2  
- python-docx  
- ReportLab  
- Google Sheets API  
- Slack Webhooks  

---

## 🛟 Support
Issues:  
https://github.com/coder-adi6/AI-Powered-Regulatory-Compliance-Checker-for-Contracts/issues

---

## 📜 License
MIT License © 2025 Aditya Goswami
