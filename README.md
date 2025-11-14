# AI-Powered Regulatory Compliance Checker

Automatically analyze contracts for GDPR, HIPAA, CCPA, and SOX compliance using AI.

## Quick Start

1. **Install Python 3.9+**

2. **Clone and Setup**
```bash
git clone https://github.com/jagadishbevera152005-sys/AI-Powered-Regulatory-Compliance-Checker.git
cd AI-Powered-Regulatory-Compliance-Checker
python -m venv .venv
.venv\Scripts\Activate.ps1  # Windows
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

3. **Configure API Key**
Create `.env` file:
```
GROQ_API_KEY=your_groq_api_key_here
```
Get free key at: https://console.groq.com/keys

4. **Run**
```bash
streamlit run app.py
```
Open browser to http://localhost:8501

## Features

- Upload contracts (PDF, DOCX, TXT)
- AI-powered compliance analysis
- GDPR support (176 requirements)
- Risk assessment and scoring
- Export reports (PDF, JSON, CSV)
- Google Sheets & Slack integration

## Usage

1. Upload your contract
2. Select GDPR framework
3. Click "Analyze Contract"
4. Review compliance score and recommendations
5. Export results

## Requirements

- Python 3.9+
- 4GB RAM
- Internet connection
- Groq API key (free)

## Support

Issues: (https://github.com/coder-adi6/AI-Powered-Regulatory-Compliance-Checker-for-Contracts/issues)

## License

MIT License - Copyright © 2025
