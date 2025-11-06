# 1. Start from an official Python base image
FROM python:3.11-slim

# --- NEW: Install system dependencies ---
# We need Tesseract for OCR (scanned PDFs)
# We need Ghostscript and OpenCV (via tk) for Camelot (PDF tables)
# We need poppler-utils for pdf2image (scanned PDFs)
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    ghostscript \
    tk \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*
# --- End of NEW ---

# 2. Set the working directory inside the container
WORKDIR /app

# 3. Copy only the requirements file first (for better caching)
COPY requirements.txt requirements.txt

# 4. Install all the Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy the rest of your application code into the container
COPY . .

# 6. Expose the port that FastAPI will run on (port 8000)
EXPOSE 8000

# 7. Define the command to run your app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]