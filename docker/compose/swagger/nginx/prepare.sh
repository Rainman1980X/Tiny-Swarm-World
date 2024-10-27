#!/bin/bash

# Configuration variables
NEXUS_URL="127.0.0.1:5000"                     # Nexus Docker Registry URL
NEW_PASSWORD="MyAdminPassWord1234-126354654"
USER_NAME="admin"
IMAGE_NAME="swagger-nginx"                     # Name of the Docker image
TAG="latest"                                   # Tag for the Docker image
DOCKERFILE_PATH="Dockerfile"                   # Path to the Dockerfile


# Generate the Dockerfile
cat <<EOF > "$DOCKERFILE_PATH"
# Base image
FROM nginx:mainline-alpine

# Kopiere die NGINX-Konfigurationsdatei in das Bild
COPY default.conf /etc/nginx/conf.d/default.conf
COPY wait-for-it.sh /wait-for-it.sh
RUN chmod +x /wait-for-it.sh
CMD ["/wait-for-it.sh", "swagger-api:8000", "--", "nginx", "-g", "daemon off;"]
EOF

docker build -t "$NEXUS_URL/$IMAGE_NAME:$TAG" -f "$DOCKERFILE_PATH" .

# Build the Docker image
docker build -t "$NEXUS_URL/$IMAGE_NAME:$TAG" "$DOCKERFILE_DIR"

# Login to Nexus repository (replace 'admin' and 'password' with your Nexus credentials)
docker login -u "$USER_NAME" -p "$NEW_PASSWORD" "$NEXUS_URL"

# Push the Docker image to Nexus repository
docker push "$NEXUS_URL/$IMAGE_NAME:$TAG"

# Logout from the Nexus repository
docker logout "$NEXUS_URL"

echo "Image $NEXUS_URL/$IMAGE_NAME:$TAG has been successfully pushed to Nexus repository."
