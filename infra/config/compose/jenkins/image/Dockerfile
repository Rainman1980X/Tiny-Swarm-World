FROM jenkins/jenkins:2.492.3-lts-jdk17

ENV JAVA_OPTS="-Djenkins.install.runSetupWizard=false -XX:ActiveProcessorCount=2 -Xms256m -Xmx1024m"

COPY setup.groovy /usr/share/jenkins/ref/init.groovy.d/setup.groovy

USER jenkins
