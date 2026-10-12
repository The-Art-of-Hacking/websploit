# Copyright (C) 2019-2026 Omar Santos <https://websploit.org>
# SPDX-License-Identifier: GPL-3.0-or-later
# Additional terms under GNU GPL version 3 section 7 are in the COPYRIGHT file.

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