# Stage 1: Install dependencies
FROM node:18-alpine AS base
RUN npm install -g pnpm

FROM base AS deps
WORKDIR /app
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile --prod=false # devDependencies も含めてインストール

# Stage 2: Build the application
FROM base AS builder
WORKDIR /app

# ビルドに必要な設定ファイル等を先にコピー
COPY --from=deps /app/node_modules ./node_modules/
COPY package.json pnpm-lock.yaml ./
COPY tsconfig.json ./
COPY next.config.js ./
COPY postcss.config.js ./
COPY tailwind.config.ts ./

# 環境変数を設定 (ARG は ENV の前に必要)
ARG NEXT_PUBLIC_API_URL
ARG NEXT_PUBLIC_API_KEY
ARG NEXT_PUBLIC_ENVIRONMENT=dev
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
ENV NEXT_PUBLIC_API_KEY=${NEXT_PUBLIC_API_KEY}
ENV NEXT_PUBLIC_ENVIRONMENT=${NEXT_PUBLIC_ENVIRONMENT}

# ソースコードをコピー
COPY . ./

# --- デバッグ情報ここから ---
RUN echo "--- Debug: Listing files in /app ---"
RUN ls -la
RUN echo "--- Debug: Checking tsconfig.json content ---"
RUN cat tsconfig.json
RUN echo "--- Debug: Checking presence of target lib file ---"
RUN ls -l ./app/lib/api.ts
RUN echo "--- Debug: End ---"
# --- デバッグ情報ここまで ---

# アプリケーションをビルド
RUN pnpm run build

# Stage 3: Production image
FROM node:18-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production
ARG NEXT_PUBLIC_API_KEY
ENV NEXT_PUBLIC_API_KEY=${NEXT_PUBLIC_API_KEY}
# Uncomment the following line in case you want to disable telemetry during runtime.
# ENV NEXT_TELEMETRY_DISABLED 1

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# publicディレクトリは存在しないため、このコピーは不要
# COPY --from=builder /app/public ./public/

# Automatically leverage output traces to reduce image size
# https://nextjs.org/docs/advanced-features/output-file-tracing
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static/

USER nextjs

EXPOSE 3000

ENV PORT 3000
# set hostname to localhost
ENV HOSTNAME "0.0.0.0"

CMD ["node", "server.js"]

RUN echo "Using environment: ${NEXT_PUBLIC_ENVIRONMENT}"