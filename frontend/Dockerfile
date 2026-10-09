FROM node:20-alpine

WORKDIR /app

# Cache dependencies
COPY package*.json ./
RUN npm install

# Copy application source
COPY . .

EXPOSE 5173

# Vite listens on 0.0.0.0 to be reachable from outside the container
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]