#!/usr/bin/env python3
"""
Config Module - Unified configuration management
统一配置管理：支持 YAML 文件 + 环境变量 + 默认值三级覆盖
"""

import os
import yaml
from typing import Dict, List, Any
from pathlib import Path


class Config:
    """Unified configuration manager"""

    def __init__(self, config_path: str = "config/settings.yaml"):
        self.config_path = config_path
        self._data = {}
        self._load()

    def _load(self) -> None:
        """Load configuration from YAML and environment variables"""
        # 1. Load YAML defaults
        if os.path.exists(self.config_path):
            with open(self.config_path, "r", encoding="utf-8") as f:
                self._data = yaml.safe_load(f) or {}
        else:
            self._data = {}

        # 2. Load keywords from separate file if exists
        keywords_path = "config/keywords.yaml"
        if os.path.exists(keywords_path):
            with open(keywords_path, "r", encoding="utf-8") as f:
                kw_data = yaml.safe_load(f) or {}
                if "keywords" in kw_data:
                    self._data.setdefault("search", {})
                    self._data["search"]["keywords"] = kw_data["keywords"]

        # 3. Environment variable overrides
        self._env_override()

    def _env_override(self) -> None:
        """Override config with environment variables"""
        env_map = {
            "SMTP_SERVER": ["email", "smtp_server"],
            "SMTP_PORT": ["email", "smtp_port"],
            "SMTP_USER": ["email", "smtp_user"],
            "SMTP_PASSWORD": ["email", "smtp_password"],
            "EMAIL_TO": ["email", "receivers"],
            "OPENAI_API_KEY": ["llm", "api_key"],
            "OPENAI_BASE_URL": ["llm", "base_url"],
            "OPENAI_MODEL": ["llm", "model"],
            "NCBI_API_KEY": ["search", "ncbi_api_key"],
            "MAX_RESULTS": ["search", "max_results"],
            "DIGEST_LANGUAGE": ["digest", "language"],
        }

        for env_key, path in env_map.items():
            value = os.environ.get(env_key)
            if value is not None:
                # Navigate nested dict
                target = self._data
                for key in path[:-1]:
                    target.setdefault(key, {})
                    target = target[key]
                # Type conversion
                final_key = path[-1]
                if final_key in ("smtp_port", "max_results"):
                    target[final_key] = int(value)
                elif final_key == "receivers":
                    target[final_key] = [r.strip() for r in value.split(",")]
                else:
                    target[final_key] = value

    def get(self, *keys: str, default: Any = None) -> Any:
        """Get nested config value: config.get('search', 'keywords')"""
        target = self._data
        for key in keys:
            if isinstance(target, dict) and key in target:
                target = target[key]
            else:
                return default
        return target

    @property
    def search_keywords(self) -> List[str]:
        return self.get("search", "keywords", default=[
            "structural variation", "genome assembly",
            "long-read sequencing", "Hi-C"
        ])

    @property
    def max_results(self) -> int:
        return self.get("search", "max_results", default=15)

    @property
    def sources(self) -> List[str]:
        return self.get("search", "sources", default=["arxiv", "pubmed", "biorxiv"])

    @property
    def digest_language(self) -> str:
        return self.get("digest", "language", default="zh")

    @property
    def llm_enabled(self) -> bool:
        return bool(self.get("llm", "api_key", default=""))

    @property
    def llm_model(self) -> str:
        return self.get("llm", "model", default="gpt-4o-mini")

    @property
    def llm_base_url(self) -> str:
        return self.get("llm", "base_url", default="https://api.openai.com/v1")

    @property
    def smtp_config(self) -> Dict[str, Any]:
        return {
            "server": self.get("email", "smtp_server", default=""),
            "port": self.get("email", "smtp_port", default=25),
            "user": self.get("email", "smtp_user", default=""),
            "password": self.get("email", "smtp_password", default=""),
            "receivers": self.get("email", "receivers", default=[]),
        }

    @property
    def github_feedback_enabled(self) -> bool:
        return bool(os.environ.get("GITHUB_TOKEN", ""))

    @property
    def github_repo(self) -> str:
        return os.environ.get("GITHUB_REPO", "")

    @property
    def scoring_config(self) -> Dict[str, Any]:
        return {
            "min_score": self.get("scoring", "min_score", default=4.0),
            "max_daily_papers": self.get("scoring", "max_daily_papers", default=15),
        }


# Global config instance
config = Config()
