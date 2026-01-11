FROM python:3.12-slim

# Set the working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application
COPY app.py .

# Expose the port
EXPOSE 5020

# Run the application
CMD ["python", "app.py"]
