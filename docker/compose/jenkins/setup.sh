#!/bin/bash

JENKINS_URL="http://localhost:8080"
JENKINS_CLI="/usr/share/jenkins/jenkins-cli.jar"
SCRIPT="/usr/share/jenkins/ref/init.groovy.d/setup.groovy"

# Wait for Jenkins to be fully up and running
sleep 60

# Run the setup script
java -jar $JENKINS_CLI -s $JENKINS_URL groovy = < $SCRIPT
