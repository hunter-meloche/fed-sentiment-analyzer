FROM python:3.11-slim

WORKDIR /app

# Install CPU-only torch first (much smaller than default CUDA build)
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download NLTK data at build time
RUN python -c "import nltk; nltk.download('punkt'); nltk.download('punkt_tab')"

COPY . .

EXPOSE 8000

# HuggingFace model cache is mounted as a volume to avoid re-downloading on rebuild
CMD ["python", "app.py"]
