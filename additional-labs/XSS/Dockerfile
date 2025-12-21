FROM python:3.14-slim

WORKDIR /app

# Copy the xss_app.py file
COPY xss_app.py .

# Copy the requirements.txt file
COPY requirements.txt .

# Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port
EXPOSE 5011

# Run the application
CMD ["python", "xss_app.py"]