FROM nats:2.10-alpine
COPY infra/railway-nats/nats-server.conf /etc/nats/nats-server.conf
# PORT env used by Railway for healthcheck — points to HTTP monitor
ENV PORT=8222
EXPOSE 4222 8222
CMD ["nats-server", "--config", "/etc/nats/nats-server.conf"]
