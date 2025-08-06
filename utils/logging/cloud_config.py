"""
Cloud logging configuration for AWS CloudWatch, Google Cloud Logging, etc.

This module provides cloud-specific logging handlers that can be easily
enabled through environment variables without changing application code.
"""

import os
import logging
from typing import Optional, Dict, Any

# Optional cloud logging dependencies
try:
    import boto3
    import watchtower
    CLOUDWATCH_AVAILABLE = True
except ImportError:
    CLOUDWATCH_AVAILABLE = False

try:
    from google.cloud import logging as gcp_logging
    GCP_LOGGING_AVAILABLE = True
except ImportError:
    GCP_LOGGING_AVAILABLE = False

try:
    from azure.monitor.opentelemetry.exporter import AzureMonitorLogExporter
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False


class CloudLoggingConfig:
    """
    Cloud logging configuration that can be enabled via environment variables.
    
    Environment Variables:
        CLOUD_PROVIDER: aws, gcp, azure
        AWS_LOG_GROUP: CloudWatch log group name
        AWS_LOG_STREAM: CloudWatch log stream name (optional)
        GCP_PROJECT_ID: Google Cloud project ID
        AZURE_CONNECTION_STRING: Azure Monitor connection string
    """
    
    def __init__(self):
        self.cloud_provider = os.getenv("CLOUD_PROVIDER", "").lower()
        self.enabled = self.cloud_provider in ["aws", "gcp", "azure"]
        
        # AWS CloudWatch configuration
        self.aws_log_group = os.getenv("AWS_LOG_GROUP", "fantasy-draft-engine")
        self.aws_log_stream = os.getenv("AWS_LOG_STREAM")  # Optional, auto-generated if not provided
        self.aws_region = os.getenv("AWS_REGION", "us-west-2")
        
        # Google Cloud configuration
        self.gcp_project_id = os.getenv("GCP_PROJECT_ID")
        
        # Azure configuration
        self.azure_connection_string = os.getenv("AZURE_CONNECTION_STRING")
    
    def create_cloud_handler(self, service_name: str) -> Optional[logging.Handler]:
        """
        Create a cloud logging handler based on the configured provider.
        
        Args:
            service_name: Name of the service for log stream naming
            
        Returns:
            Configured cloud logging handler or None if not available/configured
        """
        if not self.enabled:
            return None
        
        if self.cloud_provider == "aws":
            return self._create_cloudwatch_handler(service_name)
        elif self.cloud_provider == "gcp":
            return self._create_gcp_handler(service_name)
        elif self.cloud_provider == "azure":
            return self._create_azure_handler(service_name)
        
        return None
    
    def _create_cloudwatch_handler(self, service_name: str) -> Optional[logging.Handler]:
        """Create AWS CloudWatch logging handler."""
        if not CLOUDWATCH_AVAILABLE:
            print(f"Warning: CloudWatch logging requested but 'watchtower' and 'boto3' not installed")
            return None
        
        try:
            # Use provided stream name or generate one
            stream_name = self.aws_log_stream or f"{service_name}-{os.getenv('ENVIRONMENT', 'dev')}"
            
            handler = watchtower.CloudWatchLogsHandler(
                log_group=self.aws_log_group,
                stream_name=stream_name,
                use_queues=False,  # For immediate logging, set True for better performance
                send_interval=60,  # Send logs every 60 seconds
                max_batch_size=10000,
                max_batch_count=10000
            )
            
            print(f"✅ CloudWatch logging enabled: {self.aws_log_group}/{stream_name}")
            return handler
            
        except Exception as e:
            print(f"❌ Failed to initialize CloudWatch logging: {e}")
            return None
    
    def _create_gcp_handler(self, service_name: str) -> Optional[logging.Handler]:
        """Create Google Cloud Logging handler."""
        if not GCP_LOGGING_AVAILABLE:
            print(f"Warning: GCP logging requested but 'google-cloud-logging' not installed")
            return None
        
        if not self.gcp_project_id:
            print(f"Warning: GCP logging requested but GCP_PROJECT_ID not set")
            return None
        
        try:
            client = gcp_logging.Client(project=self.gcp_project_id)
            handler = client.get_default_handler()
            
            # Add service label
            handler.resource.labels['service_name'] = service_name
            
            print(f"✅ GCP logging enabled for project: {self.gcp_project_id}")
            return handler
            
        except Exception as e:
            print(f"❌ Failed to initialize GCP logging: {e}")
            return None
    
    def _create_azure_handler(self, service_name: str) -> Optional[logging.Handler]:
        """Create Azure Monitor logging handler."""
        if not AZURE_AVAILABLE:
            print(f"Warning: Azure logging requested but 'azure-monitor-opentelemetry-exporter' not installed")
            return None
        
        if not self.azure_connection_string:
            print(f"Warning: Azure logging requested but AZURE_CONNECTION_STRING not set")
            return None
        
        try:
            exporter = AzureMonitorLogExporter(
                connection_string=self.azure_connection_string
            )
            
            # Create a custom handler that works with the Azure exporter
            handler = AzureLoggingHandler(exporter, service_name)
            
            print(f"✅ Azure Monitor logging enabled")
            return handler
            
        except Exception as e:
            print(f"❌ Failed to initialize Azure logging: {e}")
            return None
    
    def get_cloud_metadata(self, service_name: str) -> Dict[str, Any]:
        """Get cloud-specific metadata for structured logging."""
        metadata = {
            "cloud_provider": self.cloud_provider,
            "service_name": service_name,
            "environment": os.getenv("ENVIRONMENT", "development")
        }
        
        if self.cloud_provider == "aws":
            metadata.update({
                "aws_region": self.aws_region,
                "log_group": self.aws_log_group,
                "instance_id": os.getenv("AWS_INSTANCE_ID"),
                "task_arn": os.getenv("ECS_TASK_ARN")  # For ECS deployments
            })
        elif self.cloud_provider == "gcp":
            metadata.update({
                "project_id": self.gcp_project_id,
                "instance_id": os.getenv("GCP_INSTANCE_ID"),
                "zone": os.getenv("GCP_ZONE")
            })
        elif self.cloud_provider == "azure":
            metadata.update({
                "resource_group": os.getenv("AZURE_RESOURCE_GROUP"),
                "subscription_id": os.getenv("AZURE_SUBSCRIPTION_ID")
            })
        
        return metadata


class AzureLoggingHandler(logging.Handler):
    """Custom logging handler for Azure Monitor integration."""
    
    def __init__(self, exporter, service_name: str):
        super().__init__()
        self.exporter = exporter
        self.service_name = service_name
    
    def emit(self, record: logging.LogRecord):
        """Emit a log record to Azure Monitor."""
        try:
            # Convert log record to Azure Monitor format
            log_data = {
                'name': 'microsoft.applicationinsights.message',
                'data': {
                    'message': self.format(record),
                    'severityLevel': self._get_severity_level(record.levelno),
                    'properties': {
                        'service_name': self.service_name,
                        'logger_name': record.name,
                        'level': record.levelname,
                        'module': record.module,
                        'function': record.funcName,
                        'line': record.lineno
                    }
                }
            }
            
            # Add any extra fields from the record
            for key, value in record.__dict__.items():
                if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                              'filename', 'module', 'lineno', 'funcName', 'created', 'msecs', 
                              'relativeCreated', 'thread', 'threadName', 'processName', 
                              'process', 'getMessage', 'exc_info', 'exc_text', 'stack_info']:
                    log_data['data']['properties'][key] = str(value)
            
            self.exporter.export([log_data])
            
        except Exception as e:
            # Don't let logging errors crash the application
            print(f"Error sending log to Azure Monitor: {e}")
    
    def _get_severity_level(self, level_no: int) -> int:
        """Convert Python logging level to Azure Monitor severity level."""
        if level_no >= logging.CRITICAL:
            return 4  # Critical
        elif level_no >= logging.ERROR:
            return 3  # Error
        elif level_no >= logging.WARNING:
            return 2  # Warning
        elif level_no >= logging.INFO:
            return 1  # Information
        else:
            return 0  # Verbose


# Global instance
_cloud_config = CloudLoggingConfig()


def get_cloud_handler(service_name: str) -> Optional[logging.Handler]:
    """
    Get a cloud logging handler for the specified service.
    
    This is the main entry point for cloud logging integration.
    """
    return _cloud_config.create_cloud_handler(service_name)


def get_cloud_metadata(service_name: str) -> Dict[str, Any]:
    """Get cloud-specific metadata for structured logging."""
    return _cloud_config.get_cloud_metadata(service_name)


def is_cloud_logging_enabled() -> bool:
    """Check if cloud logging is enabled."""
    return _cloud_config.enabled