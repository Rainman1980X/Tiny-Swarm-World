# Use Ubuntu as base image
FROM ubuntu:24.04

# Set environment variables
ENV qqy="-qq -y -o=Dpkg::Use-Pty=0"
ENV JAVA_HOME=/usr/lib/jvm/jdk-21
ENV M2_HOME=/opt/maven
ENV GRADLE_HOME=/opt/gradle
ENV PATH=$JAVA_HOME/bin:$M2_HOME/bin:$GRADLE_HOME/bin:$PATH
ENV JAVA_OPTS -Djenkins.install.runSetupWizard=false

# Install required packages
RUN apt-get update $qqy && apt-get install $qqy \
    curl \
    wget \
    git \
    unzip \
    gnupg \
    software-properties-common \
    openjdk-21-jdk \
    && rm -rf /var/lib/apt/lists/*

# Add Jenkins GPG key and repository
RUN wget -O /usr/share/keyrings/jenkins-keyring.asc https://pkg.jenkins.io/debian-stable/jenkins.io-2023.key && \
    echo "deb [signed-by=/usr/share/keyrings/jenkins-keyring.asc] https://pkg.jenkins.io/debian-stable binary/" | \
    tee /etc/apt/sources.list.d/jenkins.list > /dev/null

# Install Jenkins
RUN apt-get update $qqy && apt-get install $qqy jenkins && chmod 644 /usr/share/java/jenkins.war

# Ensure init.groovy.d directory exists and copy Groovy script
RUN mkdir -p /usr/share/jenkins/ref/init.groovy.d
COPY setup.groovy /usr/share/jenkins/ref/init.groovy.d/

# Set file permissions
RUN chmod 755 /usr/share/jenkins/ref/init.groovy.d/setup.groovy

# Skip Jenkins setup wizard
RUN echo 2.0 > /var/lib/jenkins/jenkins.install.UpgradeWizard.state && chmod 644 /var/lib/jenkins/jenkins.install.UpgradeWizard.state

# Ensure Jenkins home directory permissions
RUN chown -R jenkins:jenkins /var/lib/jenkins

# Expose Jenkins ports
EXPOSE 8080 50000

# Switch to Jenkins user and start Jenkins
USER jenkins
CMD ["java", "-jar", "/usr/share/java/jenkins.war"]
