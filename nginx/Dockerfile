FROM nginx:1.29.4-alpine

# Remove default config
RUN rm /etc/nginx/conf.d/default.conf

# Copy custom config
COPY nginx.conf /etc/nginx/nginx.conf

# Create directories for static and media
RUN mkdir -p /app/staticfiles /app/media

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost/health/ || exit 1

EXPOSE 80 443

CMD ["nginx", "-g", "daemon off;"]