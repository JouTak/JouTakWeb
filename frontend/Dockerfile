# syntax=docker/dockerfile:1.7

FROM node:24.18.0-alpine@sha256:a0b9bf06e4e6193cf7a0f58816cc935ff8c2a908f81e6f1a95432d679c54fbfd AS build
WORKDIR /app
COPY package.json package-lock.json ./
COPY prepare-husky.mjs ./
RUN --mount=type=cache,target=/root/.npm \
    npm ci --no-audit --no-fund
COPY . .
RUN npm run build

FROM nginxinc/nginx-unprivileged:1.27-alpine@sha256:65e3e85dbaed8ba248841d9d58a899b6197106c23cb0ff1a132b7bfe0547e4c0

USER root
RUN rm -rf /usr/share/nginx/html/*
COPY --from=build --chown=101:101 /app/dist /usr/share/nginx/html
COPY --chown=101:101 nginx.conf /etc/nginx/conf.d/default.conf
COPY entrypoint.sh /entrypoint.sh
RUN chmod 0755 /entrypoint.sh && chown 101:101 /entrypoint.sh

USER 101

EXPOSE 8080
ENTRYPOINT ["/entrypoint.sh"]
CMD ["nginx", "-g", "daemon off;"]
