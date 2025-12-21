FROM python:3.14-slim

WORKDIR /app

# Copy the sqli-example-app.py file
COPY sqli-example-app.py .

# Install the dependencies
RUN pip install flask

# Expose the port
EXPOSE 5000

# Run the application
CMD ["python", "sqli-example-app.py"]

