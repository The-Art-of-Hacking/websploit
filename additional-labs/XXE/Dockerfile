FROM python:3.14-slim

WORKDIR /app

# Copy the xxe_app.py file
COPY xxe_app.py .

# Install the dependencies
RUN pip install flask requests urllib3

# Expose the port
EXPOSE 5014

# Run the application   
CMD ["python", "xxe_app.py"]

