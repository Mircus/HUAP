"""
HUAP CLI - Command-line interface for pod development, tracing, and evaluation.

Pod Commands:
- huap pod create <name> - Create a new pod from template
- huap pod validate <name> - Validate a pod's contract implementation
- huap pod list - List all registered pods

Agent Commands:
- huap agent new <name> - Scaffold a new agent program
- huap agent run <agent> <task> - Run an agent on a task
- huap agent list [--pod <name>] - List registered agents

Trace Commands:
- huap trace run <pod> <graph> - Run a graph with tracing
- huap trace replay <trace.jsonl> - Replay a trace with stubs
- huap trace diff <baseline> <candidate> - Compare two traces
- huap trace view <trace.jsonl> - View events in a trace

Eval Commands:
- huap eval run <suite> - Evaluate a suite of traces
- huap eval trace <trace.jsonl> - Evaluate a single trace
- huap eval init - Create default budget config
- huap eval grades - Show grade thresholds

CI Commands:
- huap ci check <suite> - Run full CI check (replay + eval)
- huap ci status - Show status from last CI run
- huap ci init - Initialize CI configuration

Message Commands:
- huap messages deliver --once - Run message delivery once
- huap messages deliver --loop - Run continuous delivery loop
- huap messages stats - Show messaging statistics
- huap messages cleanup - Clean up expired messages
- huap messages retry - Process pending retries
- huap messages list --pod <name> - List messages for a pod
"""

from .main import cli

__all__ = ["cli"]
