FROM python:3.9-slim

WORKDIR /app
COPY ssrf_app.py .
RUN pip install flask requests urllib3

EXPOSE 5000
CMD ["python", "ssrf_app.py"]