FROM node:22-alpine AS builder

WORKDIR /app

ARG VITE_GRAPH_API_BASE_URL=/api/graph
ARG VITE_CHAT_API_BASE_URL=/api/chat
ARG VITE_PIPELINE_API_BASE_URL=/api/pipeline
ENV VITE_GRAPH_API_BASE_URL=$VITE_GRAPH_API_BASE_URL \
    VITE_CHAT_API_BASE_URL=$VITE_CHAT_API_BASE_URL \
    VITE_PIPELINE_API_BASE_URL=$VITE_PIPELINE_API_BASE_URL

COPY package.json package-lock.json* ./
RUN npm install

COPY . ./
RUN npm run build

FROM nginx:alpine

RUN rm -rf /usr/share/nginx/html/*
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
