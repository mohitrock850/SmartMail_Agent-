# SmartMail Agent: An AI-Powered Gmail Assistant

<p align="center">
  <img src="./assets/demo.gif" alt="SmartMail Agent Demo GIF">
</p>

This is a complete, end-to-end AI assistant that lives directly inside Gmail. It reads, analyzes, and helps you reply to emails by summarizing content, reading attachments (including encrypted files), and drafting intelligent, human-like replies.

This project is not just a concept; it is **fully deployed and live**, running 24/7 as a containerized web service that communicates with a live Google Workspace Add-on and a permanent cloud database.

**Live Demos:**
* **[View the Live Analytics Dashboard](httpss://[YOUR-RENDER-URL-HERE].onrender.com/dashboard)**
* **[View the Live API Documentation](httpss://[YOUR-RENDER-URL-HERE].onrender.com/docs)**

---

## 🚀 Core Features

* **AI-Powered Summaries:** Uses **LangChain** and **OpenAI (GPT)** to read email content and generate concise summaries and full, human-like draft replies.
* **Advanced Attachment Processing:** The agent's "brain" can read *inside* attachments:
    * **Unencrypted Files:** Reads text from `.pdf` and `.docx` files.
    * **Tables:** Parses tables within documents (`.pdf`, `.docx`) and includes the data in its analysis.
    * **Scanned Images:** Uses **OCR (Tesseract)** to read text from scanned (image-based) PDFs.
* **Encrypted File Handling:** A core feature of this agent.
    * Automatically detects password-protected `.pdf` and `.docx` files.
    * Prompts the user for the password directly within the Gmail add-on.
    * Securely decrypts the file on the backend using `pikepdf` and `msoffcrypto` to process the hidden content.
* **"Primary Inbox" Filtering:** Intelligently ignores "Promotions" and "Social" tabs to focus only on important emails.
* **Categorization & Prioritization:** Assigns a category (e.g., "Work," "Finance") and a priority score to every email.
* **24/7 Deployment:** Runs as a Docker container on a persistent cloud service (Render).

## 🎛️ The Interface

The agent is delivered through two custom UIs:

1.  **Google Workspace Add-on:**
    * A homepage widget shows a **"Today's Digest"** of top emails.
    * When an email is opened, the sidebar automatically shows the AI summary, category, and an **editable draft reply**.
    * Provides a password prompt for encrypted files.
    * Includes a "Send" button for "human-in-the-loop" approval.
2.  **Analytics Dashboard:**
    * A separate web page (served from the same API) that visualizes all processed email data.
    * Shows a live pie chart of email categories.

---

## 🧠 Application Logic Flowchart

This diagram shows the step-by-step logic the agent follows every time you open an email.

```mermaid
graph TD
    A[Open Email in Gmail] --> B{Add-on Calls API<br>/process-email};
    B --> C{Email in DB?};
    C -- Yes --> D[Check if Encrypted<br>Placeholder];
    C -- No --> E[Fetch from Gmail API];
    E --> F{Attachment?<br>(.pdf/.docx)};
    F -- No --> G[Read Email Body];
    D -- No --> H[Return Cached DB Data];
    F -- Yes --> I[Download Attachment];
    I --> J{Is File Encrypted?};
    J -- Yes --> K[Return 'needs_password'];
    J -- No --> L[Read Text/Tables/OCR];
    G --> M(Send to AI<br>Summarize & Draft);
    L --> M;
    K --> N(Add-on Shows<br>Password Prompt);
    N --> O{User Enters Password};
    O --> P(Add-on Calls API<br>/process-document);
    P --> Q[Decrypt & Read<br>Text/Tables/OCR];
    Q --> M;
    M --> R[Save to PostgreSQL DB];
    R --> H;
    H --> S[Display Summary & Draft in Gmail];
    D -- Yes --> K;

    style A fill:#D6EAF8,stroke:#3498DB
    style S fill:#D5F5E3,stroke:#2ECC71
    style K fill:#FADBD8,stroke:#E74C3C
    style N fill:#FADBD8,stroke:#E74C3C
    style O fill:#FADBD8,stroke:#E74C3C
    style P fill:#FADBD8,stroke:#E74C3C
    style Q fill:#FADBD8,stroke:#E74C3C

## 🛠️ Tech Stack & Architecture

This project is built with a decoupled, cloud-native architecture. The frontend (Google Apps Script) is completely separate from the backend (FastAPI), communicating only through a secure REST API.

| Area | Technology | Purpose |
| :--- | :--- | :--- |
| **Backend** | Python 3.11, FastAPI | For building the robust, asynchronous API. |
| **AI** | LangChain, OpenAI | For summarization, classification, and drafting replies. |
| **Deployment** | Docker, Render | For containerizing the app and hosting it 24/7. |
| **Database** | PostgreSQL, SQLAlchemy | For permanent data storage and analysis. |
| **Frontend** | Google Apps Script | For building the native sidebar UI inside Gmail. |
| **PDF Parsing** | `pikepdf` | For robust PDF reading and decryption. |
| **Word Parsing**| `python-docx`, `msoffcrypto-tool` | For reading `.docx` files and handling encryption. |
| **Table Parsing** | `camelot-py` | For extracting tables from PDFs. |
| **OCR** | `pytesseract`, `pdf2image` | For reading text from scanned (image) PDFs. |
| **Auth** | Google OAuth 2.0 | For securely authenticating with the Gmail API. |

---

## 📸 Project Showcase

### FastAPI Documentation (Live)
Our API is fully documented using FastAPI's automatic OpenAPI spec.
<p align="center">
  <img src="./assets/fastapi_docs.png" alt="FastAPI Docs Page" width="800">
</p>

### Analytics Dashboard (Live)
A live dashboard built into the API that queries the PostgreSQL database and visualizes email categories.
<p align="center">
  <img src="./assets/dashboard.png" alt="Analytics Dashboard" width="800">
</p>

---

## 🏃‍♂️ How to Run This Project Locally

### 1. Clone the Repository
```bash
git clone [https://github.com/](https://github.com/)[YOUR-USERNAME]/[YOUR-REPO-NAME].git
2. Google Cloud Setup
Create a project, enable the Gmail API.

Create OAuth 2.0 credentials and download credentials.json.

Add your test user to the OAuth consent screen.

3. Local Setup
Install Python 3.10+.

Create and activate a virtual environment: python -m venv venv & source venv/bin/activate (or .\venv\Scripts\activate on Windows)

Install all dependencies: pip install -r requirements.txt

4. Install System Dependencies (for OCR/Tables)
Windows: You must install Poppler and Tesseract OCR and add both to your system's PATH.

macOS: brew install poppler tesseract

Linux: apt-get install poppler-utils tesseract-ocr

5. Environment Variables
Create a .env file and add your keys:

Ini, TOML

OPENAI_API_KEY="sk-..."
USER_NAME="Your Name"
6. Run One-Time Auth
Run the auth script to get your token.json file:

Bash

python cli.py
7. Run the Server
The app is now ready to run locally (it will use a local smartmail.db file).

Bash

uvicorn main:app --reload
8. Test
Open http://127.0.0.1:8000/docs to see your local API.
