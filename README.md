# 📧 SmartMail Agent: An AI-Powered Gmail Assistant

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.11-blue?logo=python&logoColor=white">
  <img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-green?logo=fastapi&logoColor=white">
  <img alt="Docker" src="https://img.shields.io/badge/Docker-blue?logo=docker&logoColor=white">
  <img alt="Render" src="https://img.shields.io/badge/Deployed%20on-Render-green?logo=render">
  <img alt="PostgreSQL" src="https://img.shields.io/badge/Database-PostgreSQL-blue?logo=postgresql&logoColor=white">
</p>

---

<p align="center">
  <img src="./demo.gif" alt="SmartMail Agent Demo" width="800">
</p>

**SmartMail Agent** is a fully deployed, end-to-end AI assistant living inside **Gmail** — summarizing, analyzing, and replying to emails with human-like precision.  
It processes encrypted attachments, categorizes emails, and runs 24/7 in the cloud.

---

## 🌐 Live Demos

- 🧠 [Analytics Dashboard](#)  
  ![Analytics Dashboard](./dashboard.png)

- ⚙️ [API Docs (Swagger UI)](#)  
  ![FastAPI Docs](./fastapi_docs.png)

---

## 🚀 Core Features

| Feature | Description |
|----------|--------------|
| 🤖 **AI Summaries** | Generates concise summaries & draft replies via **LangChain + OpenAI (GPT)** |
| 📎 **Attachment Reader** | Reads text/tables from `.pdf` & `.docx`, even scanned images (OCR via Tesseract) |
| 🔐 **Encrypted File Support** | Detects & decrypts password-protected PDFs/DOCs (`pikepdf`, `msoffcrypto`) |
| 📨 **Primary Inbox Focus** | Ignores “Promotions” & “Social” tabs |
| 🧩 **Categorization** | Auto-labels emails (Work, Finance, etc.) and assigns priority |
| ☁️ **24/7 Cloud** | Containerized & deployed with **Docker + Render** |

---

## 🖥️ Interface

### 📬 Gmail Add-on
- “**Today’s Digest**” summary view  
- Auto AI summaries & editable draft replies  
- Password prompt for encrypted files  
- Human-in-the-loop “Send” button  

### 📊 Analytics Dashboard
- Built-in FastAPI dashboard  
- Live visualization of email categories (from PostgreSQL)


---

## 🧠 Application Logic Flowchart

```mermaid
graph TD
    A[Open Email in Gmail] --> B{"Add-on Calls API<br>/process-email"};
    B --> C{"Email in DB?"};
    C -- Yes --> D["Check if Encrypted<br>Placeholder"];
    C -- No --> E[Fetch from Gmail API];
    E --> F{"Attachment?<br>(.pdf/.docx)"};
    F -- No --> G[Read Email Body];
    D -- No --> H[Return Cached DB Data];
    F -- Yes --> I[Download Attachment];
    I --> J{"Is File Encrypted?"};
    J -- Yes --> K[Return 'needs_password'];
    J -- No --> L[Read Text/Tables/OCR];
    G --> M("Send to AI<br>Summarize & Draft");
    L --> M;
    K --> N("Add-on Shows<br>Password Prompt");
    N --> O{"User Enters Password"};
    O --> P("Add-on Calls API<br>/process-document");
    P --> Q[Decrypt & Read<br>Text/Tables/OCR];
    Q --> M;
    M --> R[Save to PostgreSQL DB];
    R --> H;
    H --> S[Display Summary & Draft in Gmail];
    D -- Yes --> K;

    style A fill:#D6EAF8,stroke:#3498DB
    style S fill:#D5F5E3,stroke:#2ECC71
    style K fill:#FADBD8,stroke:#E74C3C
```

## 🛠️ Tech Stack & Architecture

| Area | Technology | Purpose |
|------|-------------|----------|
| 🧩 **Backend** | Python 3.11, FastAPI | Asynchronous REST API |
| 🧠 **AI Layer** | LangChain, OpenAI (GPT) | Summarization, classification & reply generation |
| 🐳 **Deployment** | Docker, Render | Containerization & 24/7 hosting |
| 🗄️ **Database** | PostgreSQL, SQLAlchemy | Persistent storage & analytics |
| 💻 **Frontend** | Google Apps Script | Gmail Add-on (native sidebar UI) |
| 📄 **PDF Parsing** | pikepdf | Secure decryption & text extraction |
| 📝 **Word Parsing** | python-docx, msoffcrypto | DOCX reading & encryption handling |
| 📊 **Table Extraction** | camelot-py | Extract tables from PDFs |
| 🧾 **OCR** | pytesseract, pdf2image | Read scanned (image-based) PDFs |
| 🔑 **Auth** | Google OAuth 2.0 | Secure Gmail API access |

---


## 🏃‍♂️ Run Locally

### 1️⃣ Clone Repository

```bash
git clone https://github.com/[YOUR-USERNAME]/[YOUR-REPO-NAME].git
cd [YOUR-REPO-NAME]
```

2️⃣ Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # (or .\venv\Scripts\activate on Windows)
```

3️⃣ Install Dependencies
```bash
pip install -r requirements.txt
```

### 🧩 System Dependencies (for OCR & Table Extraction)

| 🖥️ **OS** | ⚙️ **Installation Command** |
|------------|------------------------------|
| 🪟 **Windows** | Install **Poppler** + **Tesseract OCR** (add both to your system PATH) |
| 🍎 **macOS** | `brew install poppler tesseract` |
| 🐧 **Linux** | `sudo apt-get install poppler-utils tesseract-ocr` |


Create a .env file in your project root:
```bash
OPENAI_API_KEY="sk-..."
USER_NAME="Your Name"
```

🔑 Authenticate Gmail API
```bash
python cli.py
```

🚀 Run the Server
```bash
uvicorn main:app --reload
```

Then open your browser at:
👉 http://127.0.0.1:8000/docs

<p align="center"> <b>💡 SmartMail Agent — AI at your Inbox!</b> </p>
