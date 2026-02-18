"""Tests for the skill plugin architecture."""

from pathlib import Path

import pytest

from knowledge_base.skill_plugin import (
    BUILTIN_SKILLS,
    MarkdownSkillPlugin,
    SkillPlugin,
    SkillRegistry,
    build_default_registry,
)

SKILLS_DIR = Path(__file__).parent.parent / "skills"


# ── Concrete stub for testing the abstract contract ─────────────────────────


class _StubPlugin(SkillPlugin):
    """Minimal SkillPlugin implementation for testing."""

    @property
    def name(self) -> str:
        return "stub_skill"

    def get_prompt(self, context=None) -> str:
        return f"stub prompt context={context}"


# ── SkillPlugin abstract interface ──────────────────────────────────────────


def test_plugin_interface_name_and_prompt():
    plugin = _StubPlugin()
    assert plugin.name == "stub_skill"
    assert plugin.get_prompt() == "stub prompt context=None"
    assert plugin.get_prompt(context={"k": "v"}) == "stub prompt context={'k': 'v'}"


# ── MarkdownSkillPlugin ─────────────────────────────────────────────────────


def test_markdown_plugin_loads_file(tmp_path):
    (tmp_path / "my_skill.md").write_text("# Skill\nDo this.", encoding="utf-8")
    plugin = MarkdownSkillPlugin("my_skill.md", tmp_path)
    assert plugin.name == "my_skill.md"
    assert "Do this" in plugin.get_prompt()


def test_markdown_plugin_lazy_loads(tmp_path):
    (tmp_path / "lazy.md").write_text("content", encoding="utf-8")
    plugin = MarkdownSkillPlugin("lazy.md", tmp_path)
    assert plugin._prompt is None  # not yet read from disk
    plugin.get_prompt()
    assert plugin._prompt is not None


def test_markdown_plugin_caches_prompt(tmp_path):
    path = tmp_path / "cached.md"
    path.write_text("original", encoding="utf-8")
    plugin = MarkdownSkillPlugin("cached.md", tmp_path)
    first = plugin.get_prompt()
    path.write_text("changed on disk")
    second = plugin.get_prompt()
    assert first == second == "original"  # cached, not re-read


def test_markdown_plugin_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError, match="Skill file not found"):
        MarkdownSkillPlugin("nonexistent.md", tmp_path)


# ── SkillRegistry ───────────────────────────────────────────────────────────


def test_registry_register_and_get():
    registry = SkillRegistry()
    plugin = _StubPlugin()
    registry.register(plugin)
    assert registry.get("stub_skill") is plugin


def test_registry_unknown_key_raises():
    registry = SkillRegistry()
    with pytest.raises(KeyError, match="Skill not registered"):
        registry.get("nonexistent")


def test_registry_replace_plugin():
    class _First(SkillPlugin):
        @property
        def name(self): return "shared_name"
        def get_prompt(self, context=None): return "first"

    class _Second(SkillPlugin):
        @property
        def name(self): return "shared_name"
        def get_prompt(self, context=None): return "second"

    registry = SkillRegistry()
    registry.register(_First())
    registry.register(_Second())
    assert registry.get("shared_name").get_prompt() == "second"


def test_registry_list_names():
    registry = SkillRegistry()
    registry.register(_StubPlugin())
    assert "stub_skill" in registry.list_names()
    assert registry.list_names() == sorted(registry.list_names())


def test_registry_contains_and_len():
    registry = SkillRegistry()
    assert "stub_skill" not in registry
    assert len(registry) == 0
    registry.register(_StubPlugin())
    assert "stub_skill" in registry
    assert len(registry) == 1


# ── build_default_registry ──────────────────────────────────────────────────


@pytest.mark.skipif(
    not SKILLS_DIR.exists(),
    reason="skills/ directory not present",
)
def test_default_registry_loads_all_builtin_skills():
    registry = build_default_registry(SKILLS_DIR)
    assert len(registry) == len(BUILTIN_SKILLS)
    for skill_name in BUILTIN_SKILLS:
        assert skill_name in registry
        assert len(registry.get(skill_name).get_prompt()) > 100


def test_default_registry_missing_dir(tmp_path):
    """Registry is empty (not an error) when skill files are absent."""
    registry = build_default_registry(tmp_path)
    assert len(registry) == 0


def test_custom_plugin_coexists_with_builtins(tmp_path):
    """Third-party plugins register alongside built-ins."""
    (tmp_path / "custom.md").write_text("Custom prompt.", encoding="utf-8")
    registry = SkillRegistry()
    registry.register(MarkdownSkillPlugin("custom.md", tmp_path))
    registry.register(_StubPlugin())
    assert "custom.md" in registry
    assert "stub_skill" in registry
    assert registry.get("custom.md").get_prompt() == "Custom prompt."
