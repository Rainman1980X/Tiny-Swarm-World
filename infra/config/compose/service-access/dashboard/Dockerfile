FROM nginx:1.29.8-alpine

RUN sed -i 's#pid[[:space:]]\+/run/nginx.pid;#pid /tmp/nginx.pid;#' /etc/nginx/nginx.conf \
    && chown -R nginx:nginx /var/cache/nginx /var/run /var/log/nginx /usr/share/nginx/html

COPY --chown=nginx:nginx index.html /usr/share/nginx/html/index.html

USER nginx
