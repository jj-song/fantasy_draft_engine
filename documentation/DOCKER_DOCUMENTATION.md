# Docker Documentation

This document contains comprehensive Docker documentation retrieved from the official Docker docs repository.

## Docker Compose Services and Containers

### Service Configuration

Docker Compose allows you to define and run multi-container applications. Here are key concepts and examples:

#### Basic Service Definition

```yaml
services:
  web:
    image: nginx:latest
    ports:
      - "8080:80"

  db:
    image: postgres:13
    environment:
      POSTGRES_USER: example
      POSTRES_DB: exampledb
```

#### Container Capabilities

Add or remove container capabilities:

```yaml
cap_add:
  - ALL

cap_drop:
  - NET_ADMIN
  - SYS_ADMIN
```

#### Custom Container Names

```yaml
container_name: my-web-container
```

**Note**: Using custom container names prevents Compose from scaling the service beyond a single container.

#### Service Dependencies

```yaml
services:
  proxy:
    image: nginx
    volumes:
      - type: bind
        source: ./proxy/nginx.conf
        target: /etc/nginx/conf.d/default.conf
        read_only: true
    ports:
      - 80:80
    depends_on:
      - backend

  backend:
    build:
      context: backend
      target: builder
```

### Docker Compose Commands

#### Starting Services

```bash
# Start all services
$ docker compose up

# Build and start services
$ docker compose up --build

# Start in detached mode
$ docker compose up -d
```

#### Managing Services

```bash
# List running services
$ docker compose ps

# View logs
$ docker compose logs

# Stop services
$ docker compose down

# Build specific service
$ docker compose build web

# Restart specific service
$ docker compose restart web
```

#### Development Workflow

```bash
# Watch for file changes (with compose watch)
$ docker compose watch

# Rebuild specific service
$ docker compose build web
$ docker compose up --no-deps -d web
```

### Networking

#### Basic Networking

Docker Compose automatically creates a default network for services:

```yaml
services:
  web:
    build: .
    ports:
      - "8000:8000"
  db:
    image: postgres
    ports:
      - "8001:5432"
```

#### Custom Networks

```yaml
services:
  frontend:
    image: example/webapp
    networks:
      - front-tier
      - back-tier

  backend:
    image: example/backend
    networks:
      back-tier:
        aliases:
          - database

networks:
  front-tier: {}
  back-tier: {}
```

#### Network Aliases

```yaml
services:
  some-service:
    networks:
      some-network:
        aliases:
          - alias1
          - alias3
```

### Volume Management

#### Volume Types

```yaml
services:
  backend:
    image: example/backend
    volumes:
      # Named volume
      - type: volume
        source: db-data
        target: /data
        volume:
          nocopy: true
          subpath: sub
      # Bind mount
      - type: bind
        source: /var/run/postgres/postgres.sock
        target: /var/run/postgres/postgres.sock

volumes:
  db-data:
```

#### Volume Mounting

```yaml
services:
  app:
    image: node:18-alpine
    working_dir: /app
    volumes:
      - ./:/app  # Bind mount current directory
```

### Development Features

#### Compose Watch

Enable automatic rebuilding on file changes:

```yaml
services:
  api:
    build:
      context: .
    develop:
      watch:
        - action: rebuild
          path: .
        - action: sync
          path: ./src
          target: /app/src
```

#### Environment Variables

```yaml
services:
  web:
    environment:
      - DEBUG=1
      - API_KEY=secret
    env_file:
      - .env
```

### Health Checks

```yaml
services:
  db:
    image: postgres
    healthcheck:
      test: ["CMD", "pg_isready", "-U", "postgres"]
      interval: 10s
      timeout: 5s
      retries: 5
```

### Production Configuration

#### Resource Limits

```yaml
services:
  frontend:
    image: example/webapp
    deploy:
      resources:
        limits:
          memory: 512M
        reservations:
          memory: 256M
```

#### GPU Support

```yaml
services:
  model:
    gpus: 
      - driver: nvidia
        count: 2
    # Or allocate all GPUs
    # gpus: all
```

### Security

#### Privileged Mode

```yaml
services:
  app:
    privileged: true  # Run with elevated privileges
```

#### User Configuration

```yaml
services:
  app:
    user: "1000:1000"  # Run as specific user
```

#### Secrets

```yaml
services:
  app:
    secrets:
      - db-password
secrets:
  db-password:
    file: ./db_password.txt
```

### Advanced Features

#### Multiple Compose Files

Use multiple compose files for different environments:

```bash
# Base configuration
$ docker compose -f compose.yaml -f compose.prod.yaml up
```

#### Service Extensions

```yaml
# common.yaml
services:
  app:
    build: .
    environment:
      CONFIG_FILE_PATH: /code/config

# compose.yaml
services:
  webapp:
    extends:
      file: common.yaml
      service: app
    ports:
      - "8080:8080"
```

### Docker Swarm Services

#### Creating Services

```bash
# Create a service
$ docker service create --name demo alpine:latest ping 8.8.8.8

# Scale a service
$ docker service scale demo=5

# Remove a service
$ docker service rm demo
```

#### Service Management

```bash
# List services
$ docker service ls

# View service logs
$ docker service logs demo

# View service tasks
$ docker service ps demo
```

### Troubleshooting

#### Container Networking

Use netshoot for network debugging:

```bash
$ docker run -it --network todo-app nicolaka/netshoot
```

#### Host Connectivity

From container to host services:

```yaml
services:
  app:
    extra_hosts:
      - "host.docker.internal:host-gateway"
```

#### Service Discovery

Test service connectivity:

```bash
# Ping between containers on user-defined network
$ docker container attach alpine1
# ping -c 2 alpine2
```

### Best Practices

1. **Use specific image tags** instead of `latest` for production
2. **Health checks** for critical services
3. **Resource limits** to prevent resource exhaustion
4. **Multi-stage builds** to reduce image size
5. **Secrets management** for sensitive data
6. **Volume mounts** for persistent data
7. **Network isolation** for security
8. **Environment-specific configs** using multiple compose files

### Common Patterns

#### Web Application Stack

```yaml
services:
  web:
    build: .
    ports:
      - "80:8000"
    depends_on:
      db:
        condition: service_healthy
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/myapp

  db:
    image: postgres:13
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_DB=myapp
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U user"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
```

This documentation covers the essential Docker and Docker Compose concepts needed for container orchestration and multi-service applications.