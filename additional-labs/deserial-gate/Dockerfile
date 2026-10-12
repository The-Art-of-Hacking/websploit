# Copyright (C) 2019-2026 Omar Santos <https://websploit.org>
# SPDX-License-Identifier: GPL-3.0-or-later
# Additional terms under GNU GPL version 3 section 7 are in the COPYRIGHT file.

FROM python:3.14-slim

# Set the working directory
WORKDIR /app

# Install the dependencies
RUN pip install flask pyyaml

# Copy the app.py file
COPY app.py .

# Expose the port
EXPOSE 5022

# Run the application
CMD ["python", "app.py"]

