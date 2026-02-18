"""Skill plugin system — modular, swappable LLM prompt templates.

Building Block: SkillRegistry + SkillPlugin
    Input Data:  skill name string (e.g., "referee_hint_generator.md")
    Output Data: prompt string from the registered plugin's get_prompt()
    Setup Data:  skills/ directory with 6 Markdown files (built-in), or custom SkillPlugin subclass

Each skill encapsulates the prompt for one AI capability. Register custom
implementations to replace built-in Markdown prompts without changing callers.

Usage::

    registry = build_default_registry(SKILLS_DIR)
    prompt = registry.get("referee_hint_generator.md").get_prompt()
    # Swap for testing:
    registry.register(MyMockPlugin())
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from pathlib import Path

logger = logging.getLogger(__name__)

BUILTIN_SKILLS = [
    "warmup_solver.md",
    "referee_hint_generator.md",
    "referee_question_answerer.md",
    "referee_scorer.md",
    "player_question_generator.md",
    "player_guess_maker.md",
]


class SkillPlugin(ABC):
    """Abstract base class for Q21G skill plugins.

    A skill encapsulates the prompt for one AI capability.
    Subclass this to add custom backends: few-shot, chain-of-thought,
    dynamically generated prompts, or test mocks.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique skill identifier (e.g., 'referee_hint_generator.md')."""

    @abstractmethod
    def get_prompt(self, context: dict | None = None) -> str:
        """Return the skill prompt, optionally parameterized by context."""


class MarkdownSkillPlugin(SkillPlugin):
    """Default implementation: prompt loaded from a Markdown file.

    Used for all six built-in skills. The .md file is lazy-loaded on
    first access and cached for subsequent calls within the same process.
    """

    def __init__(self, skill_name: str, skills_dir: Path) -> None:
        self._name = skill_name
        self._path = skills_dir / skill_name
        if not self._path.exists():
            raise FileNotFoundError(f"Skill file not found: {self._path}")
        self._prompt: str | None = None  # lazy-loaded

    @property
    def name(self) -> str:
        return self._name

    def get_prompt(self, context: dict | None = None) -> str:
        if self._prompt is None:
            self._prompt = self._path.read_text(encoding="utf-8")
        return self._prompt


class SkillRegistry:
    """Registry of skill plugins keyed by name.

    Supports runtime replacement of any skill — useful for A/B testing
    prompt variants, injecting few-shot examples, or mocking in tests.

    Example — swap a single skill for a test::

        registry.register(MockHintPlugin())
        assert registry.get("referee_hint_generator.md") is MockHintPlugin
    """

    def __init__(self) -> None:
        self._plugins: dict[str, SkillPlugin] = {}

    def register(self, plugin: SkillPlugin) -> None:
        """Register a plugin. Replaces any existing plugin with the same name."""
        if plugin.name in self._plugins:
            logger.debug("Replacing skill plugin: %s", plugin.name)
        self._plugins[plugin.name] = plugin

    def get(self, name: str) -> SkillPlugin:
        """Return plugin by name. Raises KeyError if not registered."""
        if name not in self._plugins:
            available = ", ".join(self.list_names())
            raise KeyError(
                f"Skill not registered: '{name}'. Available: {available or 'none'}"
            )
        return self._plugins[name]

    def list_names(self) -> list[str]:
        """Sorted list of registered skill names."""
        return sorted(self._plugins)

    def __len__(self) -> int:
        return len(self._plugins)

    def __contains__(self, name: str) -> bool:
        return name in self._plugins


def build_default_registry(skills_dir: Path) -> SkillRegistry:
    """Build a SkillRegistry pre-loaded with all six built-in Markdown skills."""
    registry = SkillRegistry()
    for filename in BUILTIN_SKILLS:
        path = skills_dir / filename
        if path.exists():
            registry.register(MarkdownSkillPlugin(filename, skills_dir))
        else:
            logger.warning("Built-in skill file missing: %s", path)
    return registry
