"""
ADE Test Suite
==============
Unit tests (no Ollama required) + one integration smoke test.

Run:   pytest tests/ -v --tb=short
Smoke: pytest tests/ -v -k integration  (requires Ollama)
"""
import ast
import json
import os
import sys
import shutil
import subprocess
import pytest
from unittest.mock import patch, MagicMock

# ── Import helpers ────────────────────────────────────────────
# Ensure ADE root is importable regardless of cwd
ADE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ADE_ROOT not in sys.path:
    sys.path.insert(0, ADE_ROOT)

# ═══════════════════════════════════════════════════════════════
# COMPONENT 1: Planner — JSON extraction logic
# ═══════════════════════════════════════════════════════════════
from ai_dev_env.agents.planner import extract_json, Plan

class TestPlannerExtractJson:
    def test_clean_json(self):
        raw = '{"task_type":"model-gen","skill":"django-model-gen","target_files":[],"context_files":[],"class_name":"Foo","app_name":"core","reasoning":"ok"}'
        result = extract_json(raw)
        assert result.startswith("{")
        assert "model-gen" in result

    def test_strips_think_tags(self):
        raw = "<think>let me ponder</think>\n{\"task_type\":\"api-gen\",\"skill\":\"django-api-gen\",\"target_files\":[],\"context_files\":[],\"class_name\":\"Bar\",\"app_name\":\"core\",\"reasoning\":\"ok\"}"
        result = extract_json(raw)
        assert "<think>" not in result
        assert "api-gen" in result

    def test_strips_markdown_fences(self):
        raw = "```json\n{\"task_type\":\"bug-fix\",\"skill\":\"bug-fix\",\"target_files\":[],\"context_files\":[],\"class_name\":\"X\",\"app_name\":\"core\",\"reasoning\":\"ok\"}\n```"
        result = extract_json(raw)
        data = json.loads(result)
        assert data["task_type"] == "bug-fix"

    def test_empty_string_returns_empty(self):
        assert extract_json("") == ""

    def test_no_braces_returns_stripped(self):
        result = extract_json("  no json here  ")
        assert result == "no json here"


class TestPlanModel:
    def _valid_plan_dict(self, **overrides):
        base = {
            "task": "test task",
            "task_type": "model-gen",
            "skill": "django-model-gen",
            "target_files": ["core/models.py"],
            "context_files": [],
            "class_name": "Product",
            "app_name": "core",
            "reasoning": "testing",
        }
        base.update(overrides)
        return base

    def test_valid_plan_parses(self):
        plan = Plan.model_validate(self._valid_plan_dict())
        assert plan.task_type == "model-gen"
        assert plan.class_name == "Product"

    def test_task_field_defaults_to_empty(self):
        d = self._valid_plan_dict()
        del d["task"]
        plan = Plan.model_validate(d)
        assert plan.task == ""

    def test_invalid_task_type_raises(self):
        with pytest.raises(Exception):
            Plan.model_validate(self._valid_plan_dict(task_type="nonsense"))


# ═══════════════════════════════════════════════════════════════
# COMPONENT 2: Coder — JSON extraction & FileOperation parsing
# ═══════════════════════════════════════════════════════════════
from ai_dev_env.agents.coder import ADE_Coder, FileOperation

class TestCoderJsonExtract:
    def setup_method(self):
        self.coder = ADE_Coder()

    def test_extracts_clean_array(self):
        raw = '[{"file":"core/models.py","action":"create","content":"# hello","reasoning":"test"}]'
        result = self.coder._robust_json_extract(raw)
        assert isinstance(result, list)
        assert result[0]["file"] == "core/models.py"

    def test_strips_think_tags(self):
        raw = '<think>thinking...</think>[{"file":"x.py","action":"create","content":"pass","reasoning":"ok"}]'
        result = self.coder._robust_json_extract(raw)
        assert result is not None
        assert result[0]["file"] == "x.py"

    def test_wraps_single_object_in_list(self):
        raw = '{"file":"a.py","action":"full_replace","content":"x=1","reasoning":"patched"}'
        result = self.coder._robust_json_extract(raw)
        assert isinstance(result, list)
        assert len(result) == 1

    def test_returns_none_on_garbage(self):
        result = self.coder._robust_json_extract("not json at all !!!!")
        assert result is None

    def test_trailing_comma_tolerance(self):
        raw = '[{"file":"a.py","action":"create","content":"pass","reasoning":"ok",}]'
        result = self.coder._robust_json_extract(raw)
        assert result is not None

    def test_file_operation_normalises_operation_key(self):
        op = {
            "operation": "create",     # LLM sometimes outputs 'operation' not 'action'
            "file": "core/models.py",
            "content": "class Foo: pass",
            "reasoning": "test",
        }
        # simulate normalisation
        if "operation" in op:
            op["action"] = op.pop("operation")
        fo = FileOperation(**op)
        assert fo.action == "create"


class TestCoderApplyOperations:
    def test_create_writes_file(self, tmp_path):
        coder = ADE_Coder()
        ops = [
            FileOperation(file="core/models.py", action="create", content="# auto", reasoning="test")
        ]
        modified = coder.apply_operations(ops, str(tmp_path))
        assert "core/models.py" in modified
        assert (tmp_path / "core" / "models.py").read_text() == "# auto"

    def test_append_adds_content(self, tmp_path):
        target = tmp_path / "views.py"
        target.write_text("# existing")
        coder = ADE_Coder()
        ops = [
            FileOperation(file="views.py", action="append", content="# new", reasoning="test")
        ]
        coder.apply_operations(ops, str(tmp_path))
        assert "# new" in target.read_text()

    def test_full_replace_overwrites(self, tmp_path):
        target = tmp_path / "old.py"
        target.write_text("old content")
        coder = ADE_Coder()
        ops = [
            FileOperation(file="old.py", action="full_replace", content="new content", reasoning="test")
        ]
        coder.apply_operations(ops, str(tmp_path))
        assert target.read_text() == "new content"

    def test_replace_block_substitutes(self, tmp_path):
        target = tmp_path / "code.py"
        target.write_text("PLACEHOLDER = None")
        coder = ADE_Coder()
        ops = [
            FileOperation(
                file="code.py",
                action="replace_block",
                block_identifier="PLACEHOLDER = None",
                content="PLACEHOLDER = 42",
                reasoning="test",
            )
        ]
        coder.apply_operations(ops, str(tmp_path))
        assert target.read_text() == "PLACEHOLDER = 42"


# ═══════════════════════════════════════════════════════════════
# COMPONENT 3: Validator — stage logic (no Django project needed)
# ═══════════════════════════════════════════════════════════════
from ai_dev_env.agents.validator import ProjectValidator, ValidationInput, ValidationResult

class TestValidatorSyntaxStage:
    def test_catches_syntax_error(self, tmp_path):
        bad_py = tmp_path / "bad.py"
        bad_py.write_text("def foo(\n")  # unclosed paren = SyntaxError
        v = ProjectValidator(str(tmp_path))
        result = v.validate(ValidationInput(
            project_path=str(tmp_path),
            modified_files=["bad.py"],
            plan={}
        ))
        assert not result.passed
        assert result.stage_reached == "syntax"
        assert "bad.py" in result.fix_signal

    def test_passes_valid_python(self, tmp_path):
        """Valid Python passes syntax stage; Django check will fail (no manage.py) but
        we verify stage_reached is NOT 'syntax'."""
        good_py = tmp_path / "good.py"
        good_py.write_text("class Foo:\n    pass\n")
        v = ProjectValidator(str(tmp_path))
        result = v.validate(ValidationInput(
            project_path=str(tmp_path),
            modified_files=["good.py"],
            plan={}
        ))
        # Should fail at 'structure' (no manage.py), NOT at 'syntax'
        assert result.stage_reached != "syntax"

    def test_skips_non_python_files(self, tmp_path):
        readme = tmp_path / "README.md"
        readme.write_text("# broken {{{{")
        v = ProjectValidator(str(tmp_path))
        result = v.validate(ValidationInput(
            project_path=str(tmp_path),
            modified_files=["README.md"],
            plan={}
        ))
        # .md file skipped; should fail at structure (no manage.py), not syntax
        assert result.stage_reached != "syntax"


# ═══════════════════════════════════════════════════════════════
# COMPONENT 4: Retriever — empty-index graceful handling
# ═══════════════════════════════════════════════════════════════
from ai_dev_env.rag.retriever import retrieve, RetrievedContext

class TestRetrieverEmptyIndex:
    def test_empty_index_returns_context_without_crash(self, tmp_path):
        """retrieve() must not crash when the ChromaDB collection is empty."""
        target = tmp_path / "core" / "models.py"
        target.parent.mkdir(parents=True)
        target.write_text("# empty models")

        ctx = retrieve(str(tmp_path), "create a Product model", ["core/models.py"])
        assert isinstance(ctx, RetrievedContext)
        assert ctx.chunks == []
        assert "core/models.py" in ctx.full_files
        assert "# empty models" in ctx.full_files["core/models.py"]

    def test_missing_target_file_returns_placeholder(self, tmp_path):
        ctx = retrieve(str(tmp_path), "some task", ["nonexistent/file.py"])
        assert "nonexistent/file.py" in ctx.full_files
        assert "# File will be created." in ctx.full_files["nonexistent/file.py"]


# ═══════════════════════════════════════════════════════════════
# INTEGRATION TEST (requires Ollama running)
# ═══════════════════════════════════════════════════════════════
INTEGRATION_PROJECT = "ade_integration_test"
INTEGRATION_PATH = os.path.join(
    os.getenv("ADE_PROJECTS", os.path.expanduser("~/hub/00_own/ADE/projects")),
    INTEGRATION_PROJECT,
)

@pytest.fixture(scope="module")
def integration_project():
    """Creates a fresh Django project for the E2E integration test."""
    if os.path.exists(INTEGRATION_PATH):
        shutil.rmtree(INTEGRATION_PATH)
    os.makedirs(INTEGRATION_PATH)

    subprocess.run(["django-admin", "startproject", "config", "."], cwd=INTEGRATION_PATH, check=True)
    subprocess.run(
        [sys.executable, "manage.py", "startapp", "core"],
        cwd=INTEGRATION_PATH, check=True
    )
    subprocess.run(["git", "init"], cwd=INTEGRATION_PATH, check=True)
    subprocess.run(["git", "add", "."], cwd=INTEGRATION_PATH, check=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=INTEGRATION_PATH, check=True)
    os.makedirs(os.path.join(INTEGRATION_PATH, ".venv/bin"), exist_ok=True)

    yield INTEGRATION_PATH


@pytest.mark.integration
def test_full_agent_loop(integration_project, monkeypatch):
    """E2E: Plan → Index → Code → Validate. Requires Ollama."""
    from ade_agent import main as ade_main

    monkeypatch.setattr(
        "sys.argv",
        ["ade_agent.py", INTEGRATION_PROJECT, "Add a Profile model with bio and user fields"],
    )
    try:
        ade_main()
        models_file = os.path.join(integration_project, "core/models.py")
        content = open(models_file).read()
        assert "class Profile" in content
        assert os.path.exists(os.path.join(integration_project, ".ade_index"))
    except Exception as e:
        pytest.fail(f"ADE E2E loop failed: {e}")
