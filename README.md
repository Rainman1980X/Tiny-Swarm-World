# Tiny Swarm World

**Tiny Swarm World** is a local development and test infrastructure designed to simulate a microservices production-like environment using Docker Swarm and Multipass. The goal is to enable developers to spin up isolated, reproducible service stacks using `docker-compose` in a managed Swarm cluster.

---

## Project Purpose

This system aims to provide a complete **local testbed for microservices**. It allows you to:

- Develop and test distributed systems with real Docker Swarm orchestration
- Deploy multiple `docker-compose` stacks
- Manage and observe services via **Portainer**
- Run all components locally on WSL2 or Linux via Multipass VMs
- Recreate cloud-like environments without needing cloud infrastructure

Ideal for backend development, integration testing, or experimentation with service-based architecture.

---

## Features

- Launch and manage virtual machines with Multipass
- Automated Docker installation and Swarm initialization
- Centralized management via **Portainer**
- Pre-integrated services:
  - Nexus (local Docker + Maven repository)
  - Jenkins (CI/CD with configuration-as-code)
  - RabbitMQ (message broker)
  - SonarQube (static code analysis)
  - Swagger + NGINX (API documentation)
- Modular infrastructure in `prepare/` and `compose/`
- Support for WSL2 port-forwarding with `socat` and `iptables`
- Async Python services for infrastructure automation
- Clear architectural separation via Hexagonal Architecture

---

## 🛠️ Requirements

- Python 3.10+
- WSL2 enabled (for Windows users)
- Multipass (QEMU backend)
- socat (for networking workaround in WSL2)
- Docker CLI

---



