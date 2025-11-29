FROM python:3.12-slim

WORKDIR /app

# Install ping utility
RUN apt-get update && apt-get install -y iputils-ping && rm -rf /var/lib/apt/lists/*

COPY cmd-injection-example-app.py .

RUN pip install flask

EXPOSE 5000

CMD ["python", "cmd-injection-example-app.py"]

