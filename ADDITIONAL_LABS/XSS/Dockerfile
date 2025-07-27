FROM python:3.9-slim

WORKDIR /app
COPY xss_app.py .
RUN pip install flask

EXPOSE 5011
CMD ["python", "xss_app.py"]