FROM node:22-alpine AS build

ARG VITE_DEMO_LOGIN_ENABLED=false
ARG VITE_DEMO_LOGIN_PASSWORD=

RUN corepack enable && corepack prepare pnpm@11.28.5 --activate
WORKDIR /app

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile

COPY . .
ENV VITE_DEMO_LOGIN_ENABLED=${VITE_DEMO_LOGIN_ENABLED}
ENV VITE_DEMO_LOGIN_PASSWORD=${VITE_DEMO_LOGIN_PASSWORD}
RUN pnpm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
