# Frontend — multi-stage production build (static assets + nginx)
FROM node:20-alpine AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

ARG VITE_API_URL
ARG VITE_TELECONSULT_PROVIDER=stub
ARG VITE_STRIPE_PUBLISHABLE_KEY=

ENV VITE_API_URL=$VITE_API_URL \
    VITE_TELECONSULT_PROVIDER=$VITE_TELECONSULT_PROVIDER \
    VITE_STRIPE_PUBLISHABLE_KEY=$VITE_STRIPE_PUBLISHABLE_KEY

RUN npm run build

FROM nginx:1.27-alpine

COPY deploy/nginx/frontend-spa.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget -qO- http://127.0.0.1/ || exit 1
