# Use Node.js 20 on alpine for a small image size
FROM node:20-alpine

# Set the working directory
WORKDIR /app

# Copy package.json and package-lock.json first for better caching
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy the rest of the frontend source code
COPY . .

# Expose the Vite default port
EXPOSE 5173

# Run the Vite dev server with --host to allow external access in Docker
CMD ["npm", "run", "dev", "--", "--host"]
