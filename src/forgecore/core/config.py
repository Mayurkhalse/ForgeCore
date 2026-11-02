from __future__ import annotations

from pathlib import Path

import yaml

from forgecore.core.models import ProjectConfig
from forgecore.core.pathguard import PathGuard

CONFIG_FILE_NAME = "project.yaml"
FORGECORE_DIR = ".forgecore"


class ConfigLoader:
    """Loads, merges and persists .forgecore/project.yaml configuration."""

    def __init__(self, root: Path | str) -> None:
        self.root = Path(root).resolve()
        self.pathguard = PathGuard(self.root)
        self.forgecore_dir = self.root / FORGECORE_DIR
        self.config_path = self.forgecore_dir / CONFIG_FILE_NAME

    def exists(self) -> bool:
        return self.config_path.is_file()

    def load(self) -> ProjectConfig:
        if not self.config_path.is_file():
            return ProjectConfig()

        try:
            content = self.pathguard.read_text(self.config_path)
            raw = yaml.safe_load(content)
            if not isinstance(raw, dict):
                return ProjectConfig()
            return ProjectConfig.model_validate(raw)
        except Exception:
            # Degrade gracefully to default if file is invalid
            return ProjectConfig()

    def save(self, config: ProjectConfig) -> Path:
        self.forgecore_dir.mkdir(parents=True, exist_ok=True)
        dump_data = config.model_dump(mode="json", exclude_none=True)
        # Clean empty defaults for prettier output
        yaml_content = yaml.dump(dump_data, sort_keys=False, default_flow_style=False)
        self.config_path.write_text(yaml_content, encoding="utf-8")
        return self.config_path

    @staticmethod
    def create_default(
        project_name: str,
        profile: str | None = None,
        add_layers: list[str] | None = None,
    ) -> ProjectConfig:
        config = ProjectConfig()
        config.project = {"name": project_name}
        config.profile = profile
        if add_layers:
            config.layers.add = add_layers
        return config
