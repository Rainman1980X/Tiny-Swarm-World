#!/bin/bash

printf "Nexus3 %s authentication used User: %s  Password: %s\n" "$NEXUS_URL" "$USER_NAME" "$NEW_PASSWORD"

# Maven Proxy Repository configuration
PROXY_REPO_NAME="maven-central-proxy"

# Check if the repository already exists
EXISTS=$(curl -u "$USER_NAME:$NEW_PASSWORD" -X GET "$NEXUS_URL/service/rest/v1/repositories" | jq -r ".[] | select(.name == \"$PROXY_REPO_NAME\") | .name")

if [ -n "$EXISTS" ]; then
    printf "Repository %s already exists. Deleting.\n" "$PROXY_REPO_NAME"

    # Perform the DELETE request
    RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" -u "$USER_NAME:$NEW_PASSWORD" -X DELETE "$NEXUS_URL/service/rest/v1/repositories/$PROXY_REPO_NAME")

    # Check if the response is a 204 No Content, which indicates success
    if [ "$RESPONSE" -eq 204 ]; then
        printf "Maven Proxy Repository '%s' deleted successfully.\n" "$PROXY_REPO_NAME"
    else
        printf "Error deleting Maven Proxy Repository. HTTP Status: %s\n" "$RESPONSE"
    fi
fi
# Create Base64 authentication header
AUTH_HEADER="Authorization: Basic $(echo -n "$USER_NAME:$NEW_PASSWORD" | base64)"

# Can be "release" or "snapshot"
REMOTE_URL="https://repo1.maven.org/maven2/"  # Remote repository URL (Maven Central)
BLOB_STORE_NAME="default"
REPO_POLICY="release"
# JSON payload to create the Maven Proxy Repository
PROXY_REPO_PAYLOAD=$(cat <<EOF
{
  "name": "$PROXY_REPO_NAME",
  "online": true,
  "storage": {
    "blobStoreName": "$BLOB_STORE_NAME",
    "strictContentTypeValidation": true
  },
  "proxy": {
    "remoteUrl": "$REMOTE_URL",
    "contentMaxAge": 1440,
    "metadataMaxAge": 1440
  },
  "negativeCache": {
    "enabled": true,
    "timeToLive": 1440
  },
  "httpClient": {
    "blocked": false,
    "autoBlock": true
  },
  "routingRule": null,
  "maven": {
    "versionPolicy": "RELEASE",
    "layoutPolicy": "STRICT"
  },
  "cleanup": {
    "policyNames": []
  }
}
EOF
)

# API call to create the Maven Proxy Repository with verbose logging (-v)
RESPONSE=$(curl -v -s -o /dev/null -w "%{http_code}" -X POST "$NEXUS_URL/service/rest/v1/repositories/maven/proxy" \
  -H "$AUTH_HEADER" \
  -H "Content-Type: application/json" \
  -d "$PROXY_REPO_PAYLOAD")

# Check if the response is successful (201 Created)
if [ "$RESPONSE" -eq 201 ]; then
    printf "Maven Proxy Repository '%s' created successfully.\n" "$PROXY_REPO_NAME"
else
    printf "Error creating Maven Proxy Repository. HTTP Status: %s\n" "$RESPONSE"

    # Additional logging for error details
    ERROR_RESPONSE=$(curl -s -X POST "$NEXUS_URL/service/rest/v1/repositories/maven/proxy" \
      -H "$AUTH_HEADER" \
      -H "Content-Type: application/json" \
      -d "$PROXY_REPO_PAYLOAD")

    if [ -n "$ERROR_RESPONSE" ]; then
        echo "Error details: $ERROR_RESPONSE"
    else
        echo "No error details received from server."
    fi
fi

