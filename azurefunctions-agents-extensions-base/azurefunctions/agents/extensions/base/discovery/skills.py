from __future__ import annotations

from pathlib import Path

from ..capabilities import SkillDefinition

_SKILL_FILE_NAME = "SKILL.md"


def _skills_root(app_root: Path) -> Path | None:
    matches: list[Path] = []
    for candidate in (app_root / "skills", app_root / "Skills"):
        if candidate.is_dir():
            resolved = candidate.resolve(strict=True)
            if resolved not in matches:
                matches.append(resolved)
    if len(matches) > 1:
        raise ValueError("Both 'skills' and 'Skills' directories exist")
    if not matches:
        return None
    skills_root = matches[0]
    if not skills_root.is_relative_to(app_root):
        raise ValueError("Skills directory resolves outside the app root")
    return skills_root


def discover_skills(app_root: Path) -> tuple[SkillDefinition, ...]:
    resolved_root = Path(app_root).resolve(strict=True)
    skills_root = _skills_root(resolved_root)
    if skills_root is None:
        return ()

    skill_files = sorted(
        skills_root.rglob(_SKILL_FILE_NAME),
        key=lambda path: path.relative_to(skills_root).as_posix().casefold(),
    )
    definitions: list[SkillDefinition] = []
    for candidate in skill_files:
        if not candidate.is_file():
            continue
        skill_file = candidate.resolve(strict=True)
        if not skill_file.is_relative_to(skills_root):
            raise ValueError(f"Skill file {str(candidate)!r} resolves outside skills")
        definitions.append(SkillDefinition(path=skill_file.parent))
    return tuple(definitions)
