# Step 2 create the mirror of maven
API_ENDPOINT="/service/rest/v1/repositories/maven/proxy"
REPO_NAME="maven-mirror"
REMOTE_URL="https://repo.maven.apache.org/maven2/"

REPO_EXISTS=$(curl -s -u "$USER_NAME:$PASSWORD" "$NEXUS_URL$API_ENDPOINT" | grep "\"name\":\"$REPO_NAME\"")

if [ -n "$REPO_EXISTS" ]; then
    printf "Repository '%s' already exists.\n" "$REPO_NAME"
else
  printf "Here the repositories setting"
fi