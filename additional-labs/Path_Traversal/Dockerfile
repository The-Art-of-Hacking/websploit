FROM python:3.14-slim

# Set the working directory
WORKDIR /app

# Install the dependencies
RUN pip install flask

# Copy the path-traversal-example-app.py file
COPY path-traversal-example-app.py .

# Expose the port
EXPOSE 5003

# Run the application
CMD ["python", "path-traversal-example-app.py"]
