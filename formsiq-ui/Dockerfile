# Stage 1: Build Angular app
FROM node:18 AS build
WORKDIR /app
COPY package*.json ./
RUN npm install
# Copy .env files if they exist (Angular setup will use them at build time)
COPY . .
# Build with production configuration
RUN npm run build -- --configuration production

# Stage 2: Serve with Nginx
FROM nginx:alpine
COPY --from=build /app/dist/formsiq-ui/browser /usr/share/nginx/html
# Configure nginx to handle Angular routing
COPY nginx.conf /etc/nginx/conf.d/default.conf 
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"] 