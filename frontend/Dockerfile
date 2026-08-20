# 阶段1: 构建前端
FROM node:20-alpine AS builder
ARG VITE_AMAP_WEB_KEY
ARG VITE_AMAP_SECURITY_CODE
ENV VITE_AMAP_WEB_KEY=${VITE_AMAP_WEB_KEY}
ENV VITE_AMAP_SECURITY_CODE=${VITE_AMAP_SECURITY_CODE}
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm config set registry https://registry.npmmirror.com && npm install
COPY . .
RUN npm run build

# 阶段2: Nginx 托管
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
