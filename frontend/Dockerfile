FROM node:25-alpine AS base

# Set working directory
WORKDIR /usr/src/app

# Copy package files
COPY ./nextjs/package.json ./nextjs/yarn.lock ./nextjs/.yarnrc.yml ./

# Install dependencies
RUN yarn install

# Copy app source
COPY ./nextjs /usr/src/app

# Expose port
EXPOSE 3000

# Default development command
CMD ["yarn", "dev"]


FROM base AS production

# Build argument for API URL (needed at build time for NEXT_PUBLIC_* vars)
ARG NEXT_PUBLIC_API_URL=""
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}

# Build the app
RUN yarn run build

# Clean cache
RUN yarn cache clean

# Start production server
CMD ["yarn", "start"]