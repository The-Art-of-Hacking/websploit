FROM python:3.14-slim

WORKDIR /app

# Copy the xss_app.py file
COPY xss_app.py .

# Install the dependencies
RUN pip install flask requests urllib3

# Expose the port
EXPOSE 5006

# Run the application
CMD ["python", "xss_app.py"]