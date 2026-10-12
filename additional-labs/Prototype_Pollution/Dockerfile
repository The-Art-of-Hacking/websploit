# Copyright (C) 2019-2026 Omar Santos <https://websploit.org>
# SPDX-License-Identifier: GPL-3.0-or-later
# Additional terms under GNU GPL version 3 section 7 are in the COPYRIGHT file.

FROM node:14-alpine

# Set the working directory
WORKDIR /usr/src/app

# Copy package files and install dependencies
COPY package.json .
RUN npm install

# Copy the application files
COPY server.js .
COPY public/ ./public/

# Expose the port
EXPOSE 5004

# Run the application
CMD [ "node", "server.js" ]
