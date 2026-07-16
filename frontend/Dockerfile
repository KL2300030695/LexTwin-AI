# Multi-stage build: compile the Vite/React app in a Node stage, then serve
# the static bundle from a lean nginx image (no Node runtime shipped).

FROM node:20-alpine AS builder

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .

# Firebase Web config must be present at BUILD time, not runtime -- Vite
# bakes import.meta.env.VITE_* values into the static bundle when it builds,
# so there's no way to configure this after the image exists (unlike a
# server-rendered app's env vars). Passed as build args rather than a
# frontend/.env file, since that file is gitignored and won't exist in the
# Docker build context -- see docker-compose.yml's frontend.build.args and
# the README's Docker mode section for where these values actually come from.
ARG VITE_FIREBASE_API_KEY
ARG VITE_FIREBASE_AUTH_DOMAIN
ARG VITE_FIREBASE_PROJECT_ID
ARG VITE_FIREBASE_APP_ID
ENV VITE_FIREBASE_API_KEY=$VITE_FIREBASE_API_KEY
ENV VITE_FIREBASE_AUTH_DOMAIN=$VITE_FIREBASE_AUTH_DOMAIN
ENV VITE_FIREBASE_PROJECT_ID=$VITE_FIREBASE_PROJECT_ID
ENV VITE_FIREBASE_APP_ID=$VITE_FIREBASE_APP_ID

RUN npm run build

FROM nginx:1.27-alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
