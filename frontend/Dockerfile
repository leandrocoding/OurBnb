FROM node:25-alpine

# Set working directory
WORKDIR /usr/src/app

# Copy app source
COPY ./nextjs /usr/src/app

# Install dependencies and build the app
RUN yarn install
RUN yarn run build
RUN yarn cache clean

# Set startup command
CMD ["yarn", "start"]
