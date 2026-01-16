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
