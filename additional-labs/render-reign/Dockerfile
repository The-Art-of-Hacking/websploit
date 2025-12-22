FROM python:3.14-slim

# Set the working directory
WORKDIR /app

# Install the dependencies
RUN pip install flask

# Copy the app.py file
COPY app.py .

# Expose the port
EXPOSE 5021

# Run the application
CMD ["python", "app.py"]

