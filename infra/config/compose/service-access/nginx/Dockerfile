FROM nginx:1.29.8-alpine

RUN sed -i 's#pid[[:space:]]\+/run/nginx.pid;#pid /tmp/nginx.pid;#' /etc/nginx/nginx.conf \
    && chown -R nginx:nginx /var/cache/nginx /var/run /var/log/nginx /etc/nginx/conf.d

COPY --chown=nginx:nginx default.conf /etc/nginx/conf.d/default.conf

USER nginx
