FROM python:3.9-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY smart_ev_charging.py .

# Run the application
CMD ["python", "-u", "smart_ev_charging.py"]
