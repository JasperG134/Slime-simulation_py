FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Stel omgevingsvariabelen in
ENV FLASK_APP=app.py
ENV FLASK_ENV=production

# Hugging Face Spaces gebruikt poort 7860
EXPOSE 7860

# Gebruik app.py voor Hugging Face
CMD ["gunicorn", "--bind", "0.0.0.0:7860", "app:app"]