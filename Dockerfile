FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Run tests first — build fails if any test fails
RUN pytest tests/ --tb=short -q

CMD ["python", "main.py"]