# Centralized Logging System

## Overview

Your Fantasy Draft Engine now has a **centralized logging system** that provides:

- **Structured JSON logs** for cloud service compatibility
- **Application lifecycle tracking** (startup, shutdown, errors)
- **Correlation IDs** for tracing requests across services
- **Automatic log rotation** (50MB files, 5 backups)
- **Cloud integration ready** (CloudWatch, GCP, Azure)
- **Centralized configuration** - one place to control all logging

## What Changed

### 1. Enhanced BaseService Class
All 6 microservices now use the enhanced BaseService with:
- Structured logging with timing information
- Application lifecycle events (🚀 startup, ✅ success, ❌ errors, 🛑 shutdown)
- Correlation ID tracking for request flows
- Enhanced error handling with full context

### 2. Centralized Log Files
All logs now go to `/logs/` directory with consistent naming:
```
logs/
├── ML Models Service.log          # Main service logs
├── ML Models Service-errors.log   # Error-only logs
├── Data Ingestion Service.log     # Main service logs  
├── Data Ingestion Service-errors.log
└── ... (one pair per service)
```

### 3. Structured Log Format
Each log entry includes:
```json
{
  "timestamp": "2025-08-06T20:41:23.456Z",
  "level": "INFO", 
  "message": "🚀 ML Models Service v1.0.0 starting up...",
  "service": {
    "name": "ML Models Service",
    "version": "1.0.0",
    "hostname": "your-machine",
    "process_id": 12345
  },
  "correlation_id": "abc-123-def",
  "event_type": "service_startup_begin"
}
```

## Features

### Application Lifecycle Tracking
Every service now logs:
- **Startup**: When service begins starting
- **Success**: When startup completes (with timing)
- **Errors**: If startup fails (with full stack traces)  
- **Shutdown**: Clean shutdown process
- **Crashes**: Unexpected failures with context

### Request Flow Tracking
- Each API request gets a **correlation ID**
- Track requests as they flow between services
- See complete request journey in logs
- Service discovery logging for inter-service calls

### Error Context
When things break, you get:
- Full stack traces
- Request context (method, path, user)
- Service context (name, version, environment)
- Correlation IDs to trace the failure

## Cloud Integration

### AWS CloudWatch
Set environment variables:
```bash
CLOUD_PROVIDER=aws
AWS_LOG_GROUP=fantasy-draft-engine
AWS_REGION=us-west-2
```

### Google Cloud Logging  
```bash
CLOUD_PROVIDER=gcp
GCP_PROJECT_ID=your-project-id
```

### Azure Monitor
```bash
CLOUD_PROVIDER=azure
AZURE_CONNECTION_STRING=your-connection-string
```

## Configuration

### Environment Variables
- `ENVIRONMENT`: development/production (affects log format)
- `LOG_LEVEL`: DEBUG/INFO/WARNING/ERROR
- `ENABLE_CLOUD_LOGGING`: true/false
- Cloud-specific variables (see above)

### Development vs Production
- **Development**: Human-readable text logs
- **Production**: Structured JSON logs for cloud parsing

## Log Rotation
- **Main logs**: 50MB max, 5 backup files
- **Error logs**: 10MB max, 3 backup files  
- Automatic cleanup of old files

## Usage in Service Code

Services automatically get enhanced logging. To use in your service logic:

```python
# In your service class
logger = self.get_logger()
contextual_logger = self.get_contextual_logger()

# Basic logging
logger.info("Processing data")

# With structured context
logger.info("User action completed", extra={
    "user_id": "123",
    "action": "generate_rankings",
    "duration_seconds": 2.5
})
```

## Monitoring Service Health

Each service automatically logs:
- **Service startup time**
- **Health check results** 
- **Error rates and types**
- **Request timing and volume**

Perfect for setting up alerts in your cloud monitoring system.

## No More Scattered Logs

Before: Logs scattered across different files, inconsistent formats
After: All logs centralized, consistent structure, easy to search and analyze

## Ready for Scale

This logging system is designed to work seamlessly with:
- Docker containers
- Kubernetes clusters
- Cloud logging services
- Log aggregation tools (ELK stack, Splunk, etc.)

---

Your centralized logging system is now active! Every service startup, API call, and error will be properly logged and traceable.