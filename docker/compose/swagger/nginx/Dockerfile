FROM nginx:mainline-alpine

# Kopiere die NGINX-Konfigurationsdatei in das Bild
COPY default.conf /etc/nginx/conf.d/default.conf
COPY wait-for-it.sh /wait-for-it.sh
RUN chmod +x /wait-for-it.sh
CMD ["/wait-for-it.sh", "swagger-api:8000", "--", "nginx", "-g", "daemon off;"]