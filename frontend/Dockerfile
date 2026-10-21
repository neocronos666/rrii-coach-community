# syntax=docker/dockerfile:1.7
FROM node:26.11.1-bookworm-slim AS base

ENV PNPM_HOME=/pnpm
ENV PATH="${PNPM_HOME}:${PATH}"

RUN corepack enable \
    && corepack prepare pnpm@11.17.0 --activate \
    && groupadd --gid 10001 app \
    && useradd --uid 10001 --gid app --create-home app

WORKDIR /app
RUN chown app:app /app

USER app

COPY --chown=app:app package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile

COPY --chown=app:app . .
RUN pnpm exec nuxt prepare

FROM base AS development

EXPOSE 3000

CMD ["pnpm", "dev", "--host", "0.0.0.0", "--port", "3000"]

FROM development AS testing
USER root
ENV PLAYWRIGHT_BROWSERS_PATH=/opt/playwright
RUN pnpm exec playwright install --with-deps chromium \
    && chown -R app:app /opt/playwright
USER app

FROM base AS build
ENV NUXT_PUBLIC_API_BASE_URL=/api/v1
RUN pnpm build

FROM node:26.11.1-bookworm-slim AS release
ENV NODE_ENV=production HOST=0.0.0.0 PORT=3000 NUXT_PUBLIC_API_BASE_URL=/api/v1
RUN groupadd --gid 10001 app \
    && useradd --uid 10001 --gid app --create-home app
WORKDIR /app
COPY --from=build --chown=app:app /app/.output ./.output
USER app
EXPOSE 3000
CMD ["node", ".output/server/index.mjs"]
