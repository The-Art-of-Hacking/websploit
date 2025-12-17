FROM python:3.9-slim

WORKDIR /app
COPY xxe_app.py .
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 5013
CMD ["python", "xxe_app.py"]

