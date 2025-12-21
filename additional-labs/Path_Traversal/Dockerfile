FROM python:3.14-slim

# Set the working directory
WORKDIR /app

# Copy the path-traversal-example-app.py file
COPY path-traversal-example-app.py .

# Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port
EXPOSE 81

# Run the application
CMD ["python", "path-traversal-example-app.py"]


