"""
Tests for huap trace wrap (P3).

Covers:
- Wraps a trivial python command
- Validates JSONL schema
- Produces run_start/run_end + stdout events
"""
import json
import os
import sys
import tempfile
from pathlib import Path


from hu_core.trace.wrap import wrap_command


class TestTraceWrap:
    def test_wraps_trivial_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "trace.jsonl")
            result = wrap_command(
                command=[sys.executable, "-c", "print('hello huap')"],
                output_path=out,
            )
            assert result["exit_code"] == 0
            assert result["event_count"] >= 3  # run_start + stdout + run_end
            assert Path(out).exists()

    def test_validates_jsonl_schema(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "trace.jsonl")
            wrap_command(
                command=[sys.executable, "-c", "print('hi')"],
                output_path=out,
            )
            with open(out) as f:
                for line in f:
                    evt = json.loads(line.strip())
                    assert "run_id" in evt
                    assert "kind" in evt
                    assert "name" in evt
                    assert "ts" in evt
                    assert "v" in evt

    def test_produces_run_start_and_run_end(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "trace.jsonl")
            wrap_command(
                command=[sys.executable, "-c", "pass"],
                output_path=out,
            )
            events = []
            with open(out) as f:
                for line in f:
                    events.append(json.loads(line.strip()))

            names = [e["name"] for e in events]
            assert "run_start" in names
            assert "run_end" in names
            assert names[0] == "run_start"
            assert names[-1] == "run_end"

    def test_captures_stdout(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "trace.jsonl")
            wrap_command(
                command=[sys.executable, "-c", "print('captured output')"],
                output_path=out,
            )
            events = []
            with open(out) as f:
                for line in f:
                    events.append(json.loads(line.strip()))

            stdout_events = [e for e in events if e["name"] == "stdout"]
            assert len(stdout_events) == 1
            assert "captured output" in stdout_events[0]["data"]["text"]

    def test_captures_stderr(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "trace.jsonl")
            wrap_command(
                command=[sys.executable, "-c", "import sys; sys.stderr.write('err\\n')"],
                output_path=out,
            )
            events = []
            with open(out) as f:
                for line in f:
                    events.append(json.loads(line.strip()))

            stderr_events = [e for e in events if e["name"] == "stderr"]
            assert len(stderr_events) == 1
            assert "err" in stderr_events[0]["data"]["text"]

    def test_nonzero_exit_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "trace.jsonl")
            result = wrap_command(
                command=[sys.executable, "-c", "raise SystemExit(42)"],
                output_path=out,
            )
            assert result["exit_code"] == 42

            events = []
            with open(out) as f:
                for line in f:
                    events.append(json.loads(line.strip()))

            end_evt = [e for e in events if e["name"] == "run_end"][0]
            assert end_evt["data"]["status"] == "error"
            assert end_evt["data"]["exit_code"] == 42

    def test_run_name_in_start_event(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "trace.jsonl")
            wrap_command(
                command=[sys.executable, "-c", "pass"],
                output_path=out,
                run_name="my_custom_run",
            )
            with open(out) as f:
                first = json.loads(f.readline().strip())
            assert first["data"]["graph"] == "my_custom_run"

    def test_duration_is_positive(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "trace.jsonl")
            result = wrap_command(
                command=[sys.executable, "-c", "pass"],
                output_path=out,
            )
            assert result["duration_ms"] > 0
