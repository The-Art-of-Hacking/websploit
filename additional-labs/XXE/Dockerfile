# Copyright (C) 2019-2026 Omar Santos <https://websploit.org>
# SPDX-License-Identifier: GPL-3.0-or-later
# Additional terms under GNU GPL version 3 section 7 are in the COPYRIGHT file.

FROM python:3.14-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y libxml2-dev libxslt-dev gcc && rm -rf /var/lib/apt/lists/*

# Copy the requirements file
COPY requirements.txt .

# Install the dependencies
RUN pip install -r requirements.txt

# Copy the xxe_app.py file
COPY xxe_app.py .

# Expose the port
EXPOSE 5014

# Run the application   
CMD ["python", "xxe_app.py"]

