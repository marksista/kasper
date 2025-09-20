#!/usr/bin/env python3
"""
Environment Detection Prometheus Exporter
Detects if running in VM, container (Docker), or real hardware
Exports result as Prometheus metric on port 8080
"""

import os
import sys
import time
import logging
import subprocess
#from typing import Optional

try:
    from prometheus_client import Gauge, start_http_server
except ImportError:
    print("Error: prometheus-client library not installed. Install with: pip install prometheus-client")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Prometheus metrics
ENVIRONMENT_TYPE = Gauge('system_environment_type', 'System environment type (0=hardware, 1=vm, 2=container)', ['environment'])

class EnvironmentDetector:
    """Detects the runtime environment (VM, Container, or Hardware)"""
    
    def is_container(self) -> bool:
        """
        Detect if running in a container by checking CPU scheduling info
        and other container-specific indicators
        """
        try:
            # Check for container-specific cgroup entries
            if os.path.exists('/proc/1/cgroup'):
                with open('/proc/1/cgroup', 'r') as f:
                    cgroup_content = f.read().lower()
                    if 'docker' in cgroup_content or 'containerd' in cgroup_content or 'kubepods' in cgroup_content:
                        return True
            
            # Check CPU scheduling info in /proc/self/cgroup
            if os.path.exists('/proc/self/cgroup'):
                with open('/proc/self/cgroup', 'r') as f:
                    cgroup_content = f.read().lower()
                    container_indicators = ['docker', 'lxc', 'containerd', 'kubepods', 'system.slice/docker']
                    if any(indicator in cgroup_content for indicator in container_indicators):
                        return True
            
            # Check for container environment variables
            container_env_vars = ['DOCKER_CONTAINER', 'container', 'KUBERNETES_SERVICE_HOST']
            if any(var in os.environ for var in container_env_vars):
                return True
                
        except Exception as e:
            logger.warning(f"Error checking container environment: {e}")
            
        return False
    
    def is_vm(self) -> bool:
        """Detect if running in a virtual machine"""
        try:
            # Try to use cpuid command if available
            result = subprocess.run(['cpuid'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                cpuid_output = result.stdout.lower()
                
                # Check for hypervisor signatures
                vm_signatures = [
                    'vmware', 'virtualbox', 'kvm', 'qemu', 'xen',
                    'hyperv', 'microsoft hv', 'parallels', 'bochs'
                ]
                
                for signature in vm_signatures:
                    if signature in cpuid_output:
                        logger.info(signature)
                        return True
                        
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            logger.debug("cpuid command not available or failed")
        
        # Try alternative method using /proc/cpuinfo
        try:
            with open('/proc/cpuinfo', 'r') as f:
                cpuinfo = f.read().lower()
                
                vm_indicators = [
                    'hypervisor', 'vmware', 'virtualbox', 'kvm', 
                    'qemu', 'xen', 'bochs', 'parallels'
                ]
                
                for indicator in vm_indicators:
                    if indicator in cpuinfo:
                        logger.info(indicator)
                        return True
                        
        except Exception as e:
            logger.debug(f"Failed to read /proc/cpuinfo: {e}")
            
        return False

    def detect_vm_windows(self):
        """Detect VM using WMI on Windows"""
        try:
            result = subprocess.run([
                'wmic', 'computersystem', 'get', 'manufacturer,model', '/format:list'
            ], capture_output=True, text=True, timeout=10, shell=True)
            
            if result.returncode == 0:
                output = result.stdout.lower()
                vm_indicators = [
                    'vmware', 'virtualbox', 'microsoft corporation',
                    'xen', 'qemu', 'parallels', 'innotek', 'bochs'
                ]
                
                for indicator in vm_indicators:
                    if indicator in output:
                        logger.info(indicator)
                        return True
        except Exception as e:
            logger.debug(f"WMI detection failed: {e}")
    
    def get_environment_type(self) -> tuple[str, int]:
        """
        Determine the environment type
        Returns: (environment_name, metric_value)
        0 = real hardware, 1 = VM, 2 = container
        """
        try:
            if self.is_container():
                return ("container", 2)
            elif self.is_vm():
                return ("vm", 1)
            elif self.detect_vm_windows():
                return ("vm", 1)
            else:
                return ("hardware", 0)
        except Exception as e:
            logger.error(f"Error detecting environment: {e}")
            return ("unknown", -1)

def update_metrics():
    """Update Prometheus metrics with current environment detection"""
    detector = EnvironmentDetector()
    
    try:
        env_name, env_value = detector.get_environment_type()
        
        # Clear previous metrics
        ENVIRONMENT_TYPE.clear()
        
        # Set the metric value
        ENVIRONMENT_TYPE.labels(environment=env_name).set(env_value)
        
        logger.info(f"Environment detected: {env_name} (value: {env_value})")
                
    except Exception as e:
        logger.error(f"Error updating metrics: {e}")
        ENVIRONMENT_TYPE.labels(environment="error").set(-1)

def main():
    """Main function to start the Prometheus metrics server"""
    try:
        update_metrics()
        # Start Prometheus metrics server on port 8080
        port = 8080
        try:
            start_http_server(port)
        except Exception as e:
            port = 8082
            logger.warning("Switched server to port 8082")
            start_http_server(port)
        finally:
            logger.info(f"Prometheus metrics server started on port {port}")
            logger.info(f"Metrics available at: http://localhost:{port}/metrics")
        input("Press any button to exit")
            
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
