from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "skill_usage.py"
spec = importlib.util.spec_from_file_location("skill_usage", SCRIPT)
usage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(usage)
NAMES = {"sde-agent", "google-ai-search", "sre-agent"}


class SkillUsageTests(unittest.TestCase):
    def test_only_tool_requests_count(self):
        self.assertEqual(usage.tool_evidence("Skill", {"skill": "sde-agent:sde-agent"}, "", NAMES),
                         {("sde-agent", "native_invocation_request")})
        self.assertEqual(usage.tool_evidence("Write", {
            "file_path": "/skills/sde-agent/SKILL.md", "content": "catalog"}, "", NAMES), set())
        self.assertEqual(usage.shell_evidence(
            'echo "cat /skills/sde-agent/SKILL.md"', "", NAMES), set())
        self.assertEqual(usage.shell_evidence(
            'python3 -c "print(\'/skills/sde-agent/SKILL.md\')"', "", NAMES), set())

    def test_reads_helpers_and_wrapped_commands(self):
        self.assertEqual(usage.shell_evidence(
            "cat /plugins/sde-agent/skills/sde-agent/SKILL.md && "
            "python3 /skills/google-ai-search/scripts/search.py --query hello", "", NAMES),
            {("sde-agent", "load_request"), ("google-ai-search", "helper_request")})
        self.assertEqual(usage.tool_evidence("exec", 'await tools.exec_command({cmd:"cat '
                         '/skills/sre-agent/SKILL.md"});', "", NAMES),
                         {("sre-agent", "wrapped_load_candidate")})
        self.assertEqual(usage.shell_evidence(
            "cd /skills/google-ai-search && python3 scripts/search.py", "", NAMES),
            {("google-ai-search", "helper_request")})

    def test_queries_and_shell_writes_do_not_count(self):
        self.assertEqual(usage.shell_evidence(
            "python3 unrelated.py --query /skills/sre-agent/scripts/check.py", "", NAMES), set())
        self.assertEqual(usage.shell_evidence("cat > /skills/sde-agent/SKILL.md", "", NAMES), set())
        self.assertEqual(usage.shell_evidence("cat <<'EOF'\n/skills/sde-agent/SKILL.md\nEOF", "", NAMES), set())

    def test_exec_respects_call_context_and_workdir(self):
        self.assertEqual(usage.tool_evidence("exec", 'text({cmd:"cat /skills/sde-agent/SKILL.md"});', "", NAMES), set())
        self.assertEqual(usage.tool_evidence("exec", '// tools.exec_command({cmd:"cat /skills/sde-agent/SKILL.md"})', "", NAMES), set())
        self.assertEqual(usage.tool_evidence("exec", 'text("tools.exec_command({cmd: \'cat /skills/sde-agent/SKILL.md\'})");', "", NAMES), set())
        self.assertEqual(usage.tool_evidence("exec", 'await tools.exec_command({cmd:"cat SKILL.md",workdir:"/skills/sde-agent"});', "", NAMES),
                         {("sde-agent", "wrapped_load_candidate")})
        self.assertEqual(usage.tool_evidence("exec", 'await tools.exec_command({cmd:"cat SKILL.md",'
                         'note:"example, workdir: \'/skills/sde-agent\', end"});', "/app", NAMES), set())
        self.assertEqual(usage.tool_evidence("exec", 'await tools.exec_command({cmd:"cat SKILL.md # example, workdir: \'/skills/sde-agent\', end"});', "/app", NAMES), set())
        self.assertEqual(usage.tool_evidence("exec", 'await tools.exec_command({justification:"example, cmd: \'cat /skills/sde-agent/SKILL.md\', end",cmd:"echo safe"});', "/app", NAMES), set())

    def test_read_cap_bounds_single_large_record(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "large.jsonl").write_text(json.dumps({"text": "x" * 100_000}))
            result = usage.summarize([("codex", root)], NAMES, None, set(), 10, 1000)
            self.assertEqual(result["coverage"]["files_truncated"], 1)
            self.assertLessEqual(result["coverage"]["bytes_read"], 1001)

    def test_aggregation_excludes_catalog_forks_old_and_maintenance(self):
        def call(call_id, command, date="2026-10-06T10:00:00Z"):
            return {"timestamp": date, "type": "response_item", "payload": {
                "type": "function_call", "call_id": call_id, "name": "exec_command",
                "arguments": json.dumps({"cmd": command})}}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            records = [{"type": "session_meta", "payload": {"id": "one", "cwd": "/app"}},
                       {"type": "response_item", "payload": {"type": "message", "role": "user",
                        "content": "/skills/sde-agent/SKILL.md"}},
                       call("a", "cat /skills/sde-agent/SKILL.md"),
                       call("b", "cat /skills/sde-agent/SKILL.md"),
                       call("old", "cat /skills/sre-agent/SKILL.md", "2025-01-01T00:00:00Z")]
            (root / "one.jsonl").write_text("\n".join(json.dumps(r) for r in records))
            (root / "fork.jsonl").write_text("\n".join(json.dumps(r) for r in [
                {"type": "session_meta", "payload": {"id": "fork", "cwd": "/app",
                 "timestamp": "2026-10-07T00:00:00Z"}},
                call("a", "cat /skills/sde-agent/SKILL.md")]))
            (root / "audit.jsonl").write_text("\n".join(json.dumps(r) for r in [
                {"type": "session_meta", "payload": {"id": "audit", "cwd": "/worktrees/yuzuru-skills"}},
                call("audit", "cat /skills/sre-agent/SKILL.md")]))
            result = usage.summarize([("codex", root)], NAMES, usage.timestamp("2026-10-01"),
                                     {"yuzuru-skills"}, 20, 1_000_000)
            self.assertEqual(result["skills"], [{"skill": "sde-agent", "sessions_with_requests": 1,
                              "evidence": {"codex:load_request": 1}}])
            self.assertEqual(result["coverage"]["excluded_sessions"], 1)
            self.assertNotIn("/app", json.dumps(result))

    def test_claude_native_invocation_and_malformed_records(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            record = {"type": "assistant", "sessionId": "x", "timestamp": "2026-10-01",
                      "message": {"content": [{"type": "tool_use", "id": "tool1", "name": "Skill",
                                  "input": {"skill": "sde-agent:sde-agent"}}]}}
            (root / "claude.jsonl").write_text("bad json\n" + json.dumps(record))
            result = usage.summarize([("claude", root)], NAMES, None, set(), 20, 1_000_000)
            self.assertEqual(result["skills"][0]["evidence"], {"claude:native_invocation_request": 1})
            self.assertEqual(result["coverage"]["malformed_records"], 1)

    def test_malformed_nested_host_records_are_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "bad.jsonl").write_text(json.dumps({"type": "response_item", "payload": "bad"}))
            result = usage.summarize([("codex", root)], NAMES, None, set(), 10, 1000)
            self.assertEqual(result["coverage"]["malformed_records"], 1)


if __name__ == "__main__":
    unittest.main()
