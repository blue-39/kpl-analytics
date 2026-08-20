FROM node:22-alpine

WORKDIR /app
RUN corepack enable
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile
COPY . .

ENV NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
EXPOSE 3000
CMD ["pnpm", "run", "dev", "--host", "0.0.0.0"]
