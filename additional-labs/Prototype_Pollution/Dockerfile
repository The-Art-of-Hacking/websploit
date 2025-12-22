FROM node:14-alpine

# Set the working directory
WORKDIR /usr/src/app

# Install the dependencies
RUN npm install

# Copy the server.js file
COPY server.js .

# Expose the port
EXPOSE 5004

# Run the application
CMD [ "node", "server.js" ]
