# ⚡ CreditIQ AI
# 🚀 Project Title
## CreditIQ – AI-Powered Credit Risk & Fraud Detection System

---

## 💡 Problem Statement

India loses ₹100 Crore daily to bad loans — not due to lack of data, but due to lack of intelligence to detect fraud and make informed credit decisions.

---

## 🛠️ Tech Stack

- **Frontend:** React.js  
- **Backend:** FastAPI (Python)  
- **Database:** ChromaDB / MongoDB  

---

## ⚙️ Features

- 📄 **Smart Document Processing (OCR):** Extracts financial data from PDFs and images  
- 🔍 **Fraud Detection Engine:** Detects circular trading, GST mismatch, and suspicious transactions  
- 📊 **AI-Based Risk Scoring:** Predicts loan default probability using ML models  
- 🧠 **Explainable AI (SHAP):** Shows reasons behind risk prediction  
- 🚨 **Early Warning System:** Identifies potential defaults before they occur  
- 📑 **Automated CAM Report:** Generates credit reports instantly  
- 💬 **Chatbot Assistant:** Explains risk, fraud, and financial insights  
- 🌐 **Multilingual Support:** English, Hindi, Marathi  

---

## ▶️ How to Run

### 🔹 Step 1: Clone the Repository
```bash
git clone  
cd your-project-folder

cd frontend
npm install
npm start

cd backend
# pip install -r requirements.txt
uvicorn main:app --reload


sign in -
email - admin@gmail.com
password - admin@123
so change the file

**India's First RBI-Compliant AI Credit Intelligence Platform**

CreditIQ AI is a powerful, automated credit appraisal engine built for the Indian mid-market lending sector. It ingests complex, messy financial documents, detects fraud, evaluates risk, and automatically writes the full Credit Appraisal Memo (CAM) natively. It takes subjective, unorganized MSME data and turns it into concrete, explainable lending decisions.

---

## 🚀 What We Have Built

1. **Intelligent Document Parsing**: Created an engine that accepts scanned, handwritten, and mixed-language (Hindi/English) PDFs like Balance Sheets, Bank Statements, and GST Filings. It bypasses simple text scraping and uses layout-aware extraction to structure the data.
2. **Real-time Early Warning System (EWS)**: Built a dynamic dashboard with live WebSocket telemetry that monitors active portfolios for volatility using simulated real-time drift algorithms. It flags upcoming defaults before they happen based on sentiment, bank flow, and GST mismatch.
3. **Advanced Risk Assessment UI**: Designed an interface that presents XGBoost Default Risk, Fraud Multipliers, Data Quality, and News Sentiment scores natively within a highly intuitive, corporate-grade React dashboard.
4. **SHAP Value Explanations**: Visualized the actual drivers behind a rejection or approval utilizing Waterfall SHAP diagrams. It shows exactly *why* a model made a decision (e.g., negative impact from high short-term debt).
5. **Generative CAM Synthesis**: Integrated Large Language Models (LLMs) to instantly generate a comprehensive, multi-page Credit Appraisal Memo synthesizing all financial records and background findings.
6. **Robust Hackathon Demo Flow**: Designed a built-in stress-test flow that takes "messy" distressed company data and successfully proves an AI-driven "REJECT" decision based on EMI bounces and plunging revenue.

---

## 🛠️ Detailed Technology Stack

### Frontend Hub
- **React.js**: The core library for building our high-speed, intuitive user interfaces.
- **Recharts**: For dynamic, SVG-based graphing of risk factors and financial data natively within React.
- **TailwindCSS**: Rapid UI styling utilizing utility-first CSS for sleek, modern, and responsive fintech dashboard layouts.

### Backend Engine
- **FastAPI (Python)**: The core orchestration framework chosen for extreme speed and native async support handling heavy I/O tasks.
- **Pandas**: Used critically for structuring, cleaning, and aggregating the extracted tabular data from messy Bank Statements and Balance Sheets.
- **SQLAlchemy**: The robust Object Relational Mapper (ORM) used to bridge our Python models with database architecture seamlessly.

### Databases
- **PostgreSQL**: The primary, heavy-duty relational database for securely storing users, comprehensive analysis histories, and generated Credit Appraisals.
- **Redis**: High-performance in-memory caching to quickly surface live Early Warning System (EWS) telemetry and manage real-time queues.


### AI / ML Engine
- **Scikit-learn**: For classic feature extraction, dimensionality reduction (PCA), and preprocessing before routing to advanced gradient boosting algorithms.
- **XGBoost**: Emulated machine learning decision trees for calculating the ultimate Probability of Default (PD) and corresponding interest rate.
- **SHAP**: Visualizing model explainability natively via Waterfall diagrams to show precisely *why* a PD score was issued. 
- **LangChain**: AI orchestration framework to chain together multi-step prompt workflows when reasoning about complex credit structures.
- **FinBERT**: Financial sentiment analysis against live news streams to flag macro-economic risks for a specific borrower.
- **ChromaDB**: A vector database implementation used underneath RAG (Retrieval-Augmented Generation) routines to query large textual audit reports instantly.
- **NetworkX**: Employed for advanced graph analysis to detect circular transactions, shell company links, and hidden related-party fraud patterns. and recorgtion.

---

## � Project Structure

The project is organized into two main directories for clean separation of concerns:

```
CreditIQ_AI/
├── frontend/                   # 🖥️ React + Vite web application
│   ├── src/                    # React components and pages
│   ├── public/                 # Static assets
│   ├── node_modules/           # JavaScript dependencies
│   ├── package.json            # Frontend dependencies
│   ├── tsconfig.json           # TypeScript config
│   ├── vite.config.ts          # Vite bundler config
│   └── ...
│
├── backend/                    # ⚙️ FastAPI Python server
│   ├── routers/                # API route definitions
│   ├── services/               # Business logic & AI services
│   ├── models/                 # ML models storage
│   ├── utils/                  # Helper functions
│   ├── data/                   # Datasets
│   ├── chroma_db/              # Vector database
│   ├── venv/                   # Python virtual environment
│   ├── main.py                 # FastAPI entry point
│   ├── config.py               # Configuration settings
│   ├── requirements.txt        # Python dependencies
│   └── ...
│
├── .env                        # 🔒 Environment variables
├── start_backend.py            # Quick start script for backend
├── start_frontend.ps1          # Quick start script for frontend (PowerShell)
├── start_frontend.sh           # Quick start script for frontend (Bash)
└── README.md                   # This file
```

---

## �🔑 External API Integrations

To run this platform successfully, CreditIQ AI requires specific API keys to connect to various data enrichment and intelligence platforms. You must create a `.env` file in the root directory (`/CreditIQ/.env`) and add the following keys. 

*Here is exactly what we used and why:*

```env
# 1. CLAUDE OPUS 4.1 API
# Purpose: The core foundational LLM used for complex logical reasoning, extracting messy unstructured text, and synthesizing the final multi-page Credit Appraisal Memo.
CLAUDE_API_KEY="your-claude-api-key"

# 2. MCA API (Ministry of Corporate Affairs)
# Purpose: Cross-checks director DINs, company registration status (CIN), and flags shell corporations automatically.
MCA_API_KEY="your-mca-api-key"

# 3. BANK STATEMENT API
# Purpose: Securely pulls digitized banking transaction data to instantly compute liquidity ratios, bouncing EMIs, and cash flow velocity.
BANK_API_KEY="your-bank-api-key"

# 4. AWS CREDENTIALS 
# Purpose: Bridges Tesseract OCR with AWS Textract to retrieve clean text from extreme low-resolution, rotated, and noisy physical invoices.
AWS_ACCESS_KEY_ID="your-aws-access-key"
AWS_SECRET_ACCESS_KEY="your-aws-secret-key"
AWS_REGION="ap-south-1"

# 5. GSTN API
# Purpose: Ingests digital tax filings (GSTR-2A/3B) directly from government portals to reconcile stated revenues against actual tax-paid invoices.
GSTN_API_TOKEN="your-gstn-api-token"
```

---

## 🏁 How to Run the Project Locally

You will need two separate terminal windows to run both the backend and frontend simultaneously. Choose the method that works best for your system.

### Quick Start (All-in-one)

For **Windows (PowerShell)**, open two terminals in the CreditIQ_AI root directory:

**Terminal 1 - Backend:**
```powershell
python start_backend.py
```

**Terminal 2 - Frontend:**
```powershell
.\start_frontend.ps1
```

For **macOS/Linux**, open two terminals:

**Terminal 1 - Backend:**
```bash
python start_backend.py
```

**Terminal 2 - Frontend:**
```bash
bash start_frontend..ps1
```

---

### Manual Setup (Detailed)

#### Backend Setup (Terminal 1)
```bash
# Navigate to the backend directory
cd backend

# Create and activate a virtual environment
# Windows
python -m venv venv
.\venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Start the FastAPI server
python run_backend.py
```

✅ **Backend will be available at:** `http://localhost:8000`
📖 **API Documentation:** `http://localhost:8000/docs`

#### Frontend Setup (Terminal 2)
```bash
# Navigate to the frontend directory
cd frontend

# Install Node.js dependencies
npm install

# Start the development server
npm run dev
```

✅ **Frontend will be available at:** `http://localhost:5173`

---

### Production Build

#### Build Frontend
```bash
cd frontend
npm run build
```

#### Build Backend
The backend is already production-ready with FastAPI. Simply ensure dependencies are installed and run with a production ASGI server:
```bash
cd backend
pip install -r requirements.txt
gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app
```

---



*Built with passion, late nights, and heavy AI engineering to bridge the gap between deep-tech and realistic Indian banking operations.*
