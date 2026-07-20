FROM oven/bun:alpine AS build

WORKDIR /app

COPY package* bun.lock* ./
RUN bun install

COPY . .
RUN bun run build

FROM nginx:1.27-alpine AS production

COPY --from=build /app/dist /usr/share/nginx/html
COPY env.template.js /usr/share/nginx/html/env.template.js
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY docker-entrypoint.d/30-runtime-env.sh /docker-entrypoint.d/30-runtime-env.sh
RUN chmod +x /docker-entrypoint.d/30-runtime-env.sh

EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]
