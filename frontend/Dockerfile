FROM node:22-alpine

WORKDIR /app

# Install dependencies first so Docker can cache this layer until package files change.
COPY package.json package-lock.json ./
RUN npm ci

COPY . .

EXPOSE 5173
CMD ["npm", "run", "dev"]
