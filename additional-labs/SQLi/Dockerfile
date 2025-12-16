FROM python:3.12-slim

WORKDIR /app

COPY sqli-example-app.py .

RUN pip install flask

EXPOSE 5000

CMD ["python", "sqli-example-app.py"]

