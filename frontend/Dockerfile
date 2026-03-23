FROM node:20-slim

WORKDIR /app/frontend

# Install deps first for better layer caching.
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

# Copy the rest of the app (source will be volume-mounted in dev).
COPY frontend ./.

EXPOSE 5173

CMD ["vite", "--host", "0.0.0.0", "--port", "5173"]

