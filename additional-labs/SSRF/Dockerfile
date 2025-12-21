FROM python:3.14-slim

WORKDIR /app

# Copy the ssrf_app.py file
COPY ssrf_app.py .

# Install the dependencies
RUN pip install flask requests urllib3

# Expose the port   
EXPOSE 5012

# Run the application
CMD ["python", "ssrf_app.py"]