"""
Pod Registry: Discover, register, and manage pods at runtime.

This module handles:
- Loading pods from config file
- Registering and unregistering pods
- Providing pod metadata and schemas
- Enforcing pod contracts
"""

import yaml
import json
import inspect
from typing import List, Dict, Any
from dataclasses import dataclass
from pathlib import Path
from importlib import import_module

from .contracts import PodContract


@dataclass
class Pod:
    """Pod metadata and configuration"""
    name: str
    enabled: bool
    package: str
    version: str
    description: str
    capabilities: List[str]
    graph_path: str


@dataclass
class PodSchema:
    """Schema for pod's session data form generation"""
    pod_name: str
    fields: List[Dict[str, Any]]


class PodRegistry:
    """
    Pod management and discovery.

    Registry pattern for managing pods at runtime.
    Loads pods from config file and provides metadata/schemas.
    """

    def __init__(self):
        """Initialize registry"""
        self._pods: Dict[str, Pod] = {}
        self._pod_instances: Dict[str, Any] = {}  # Cached pod instances

    def load_from_config(self, config_file: str) -> None:
        """
        Load pods from config file.

        Args:
            config_file: Path to config.yaml or config.json

        Raises:
            FileNotFoundError: If config file not found
            ValueError: If config format invalid
            ImportError: If pod package cannot be imported
        """
        config_path = Path(config_file)

        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_file}")

        # Load YAML or JSON
        if config_path.suffix.lower() in ['.yaml', '.yml']:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
        elif config_path.suffix.lower() == '.json':
            with open(config_path, 'r') as f:
                config = json.load(f)
        else:
            raise ValueError(f"Unsupported config format: {config_path.suffix}")

        if not config or 'pods' not in config:
            raise ValueError("Config must contain 'pods' key")

        pods_config = config['pods']
        if 'enabled' not in pods_config:
            raise ValueError("Config must contain 'pods.enabled' list")

        # Load each enabled pod
        enabled_pods = pods_config.get('enabled', [])

        for pod_name in enabled_pods:
            if pod_name not in pods_config:
                raise ValueError(f"Pod '{pod_name}' in 'enabled' list but not configured")

            pod_config = pods_config[pod_name]

            if not pod_config.get('enabled', True):
                # Pod listed but disabled, skip it
                continue

            try:
                # Import pod package to validate it exists
                import_module(pod_config['package'])

                # Create Pod object
                pod = Pod(
                    name=pod_name,
                    enabled=pod_config.get('enabled', True),
                    package=pod_config['package'],
                    version=pod_config.get('version', '0.1.0'),
                    description=pod_config.get('description', ''),
                    capabilities=pod_config.get('capabilities', []),
                    graph_path=pod_config.get('graph', f'{pod_name}.yaml')
                )

                # Register pod
                self.register(pod)

            except ImportError as e:
                raise ImportError(
                    f"Failed to import pod package '{pod_config['package']}': {e}"
                )
            except Exception as e:
                raise ValueError(
                    f"Error loading pod '{pod_name}': {e}"
                )

    def register(self, pod: Pod) -> None:
        """
        Register a pod.

        Args:
            pod: Pod to register

        Raises:
            ValueError: If pod already registered
        """
        if pod.name in self._pods:
            raise ValueError(f"Pod '{pod.name}' is already registered")

        self._pods[pod.name] = pod

    def unregister(self, pod_name: str) -> None:
        """
        Unregister a pod.

        Args:
            pod_name: Name of pod to unregister

        Raises:
            KeyError: If pod not found
        """
        if pod_name not in self._pods:
            raise KeyError(f"Pod '{pod_name}' not registered")

        del self._pods[pod_name]

        # Also remove cached instance
        if pod_name in self._pod_instances:
            del self._pod_instances[pod_name]

    def get_pod(self, pod_name: str) -> Pod:
        """
        Get pod by name.

        Args:
            pod_name: Name of pod (e.g., "hello")

        Returns:
            Pod object

        Raises:
            KeyError: If pod not found
        """
        if pod_name not in self._pods:
            raise KeyError(f"Pod '{pod_name}' not registered")

        return self._pods[pod_name]

    def list_pods(self) -> List[Pod]:
        """
        List all registered pods.

        Returns:
            List of Pod objects
        """
        return list(self._pods.values())

    def get_enabled_pods(self) -> List[Pod]:
        """
        List only enabled pods.

        Returns:
            List of enabled Pod objects
        """
        return [p for p in self._pods.values() if p.enabled]

    def is_pod_enabled(self, pod_name: str) -> bool:
        """
        Check if pod is enabled.

        Args:
            pod_name: Name of pod

        Returns:
            True if pod is enabled, False if disabled or not found
        """
        try:
            pod = self.get_pod(pod_name)
            return pod.enabled
        except KeyError:
            return False

    def get_pod_contract(self, pod_name: str) -> PodContract:
        """
        Return the PodContract implementation for a pod.
        """
        return self._get_pod_instance(pod_name)

    def get_pod_schema(self, pod_name: str) -> Dict[str, Any]:
        """
        Get pod's data schema for form generation.

        This loads the pod instance and calls its get_schema() method.

        Args:
            pod_name: Name of pod

        Returns:
            Schema dict with fields for form generation
            Example:
            {
                "pod_name": "hello",
                "fields": [
                    {
                        "name": "location",
                        "type": "select",
                        "options": ["office", "home", "gym"],
                        "required": True,
                        "description": "Where are you?"
                    }
                ]
            }

        Raises:
            KeyError: If pod not found
            AttributeError: If pod doesn't implement get_schema()
        """
        pod_instance = self._get_pod_instance(pod_name)

        if not hasattr(pod_instance, 'get_schema'):
            raise AttributeError(
                f"Pod '{pod_name}' does not implement get_schema() method"
            )

        schema = pod_instance.get_schema()

        # Convert PodSchema dataclass to dict if needed
        if isinstance(schema, PodSchema):
            return {
                "pod_name": schema.pod_name,
                "fields": schema.fields
            }

        return schema

    def get_pod_metadata(self, pod_name: str) -> Dict[str, Any]:
        """
        Get pod metadata for API responses.

        Args:
            pod_name: Name of pod

        Returns:
            Metadata dict
            {
                "name": "hello",
                "version": "0.1.0",
                "enabled": True,
                "description": "...",
                "capabilities": ["session_tracking", "ai_coaching"]
            }
        """
        pod = self.get_pod(pod_name)

        return {
            "name": pod.name,
            "version": pod.version,
            "enabled": pod.enabled,
            "description": pod.description,
            "capabilities": pod.capabilities
        }

    def _get_pod_instance(self, pod_name: str) -> Any:
        """
        Get or create pod instance (cached).

        Args:
            pod_name: Name of pod

        Returns:
            Pod instance (the actual pod module/class)

        Raises:
            KeyError: If pod not found
        """
        if pod_name in self._pod_instances:
            return self._pod_instances[pod_name]

        pod = self.get_pod(pod_name)

        try:
            pod_module = import_module(pod.package)

            instance: Any
            if hasattr(pod_module, "get_pod"):
                instance = pod_module.get_pod()
            elif hasattr(pod_module, "Pod"):
                candidate = getattr(pod_module, "Pod")
                instance = candidate() if inspect.isclass(candidate) else candidate
            else:
                instance = pod_module

            if not isinstance(instance, PodContract):
                raise TypeError(
                    f"Pod '{pod_name}' must expose a PodContract instance via get_pod()"
                )

            self._pod_instances[pod_name] = instance
            return instance

        except (ImportError, AttributeError) as e:
            raise ImportError(
                f"Failed to import pod package '{pod.package}': {e}"
            )

    def __repr__(self) -> str:
        """String representation"""
        enabled = self.get_enabled_pods()
        return (
            f"PodRegistry({len(self._pods)} pods, "
            f"{len(enabled)} enabled)"
        )
