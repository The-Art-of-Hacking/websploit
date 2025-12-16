FROM python:3.12-slim

WORKDIR /app

COPY path-traversal-example-app.py .

RUN pip install flask

EXPOSE 81

CMD ["python", "path-traversal-example-app.py"]

