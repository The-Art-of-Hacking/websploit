FROM python:3.9-slim

# Set the working directory
WORKDIR /app

# Install the dependencies
RUN pip install flask graphene flask-graphql werkzeug

# Copy the app.py file
COPY app.py .

EXPOSE 5023

CMD ["python", "app.py"]

