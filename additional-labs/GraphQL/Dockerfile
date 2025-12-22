FROM python:3.9-slim

# Set the working directory
WORKDIR /app

# Install the dependencies
# Pin versions to ensure compatibility with flask-graphql and graphene 2.x
# flask-graphql is not compatible with graphene 3.x or werkzeug 2.2+
# markupsafe<2.1.0 is needed because soft_unicode was removed in 2.1.0
RUN pip install "graphene<3" "flask-graphql" "flask<2.2" "werkzeug<2.2" "markupsafe<2.1.0"

# Copy the app.py file
COPY app.py .

EXPOSE 5023

CMD ["python", "app.py"]
