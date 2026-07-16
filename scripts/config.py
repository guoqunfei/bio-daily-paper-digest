#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""集中配置管理"""

import os
from pathlib import Path


class Config:
    def __init__(self):
        self.cfg = self._load_yaml()

    def _load_yaml(self):
        """简单 YAML 解析，不依赖外部库"""
        config_path = Path(__file__).parent.parent / "config" / "keywords.yaml"
        if not config_path.exists():
            return {}
        result = {}
        current_key = None
        current_list = []
        with open(config_path, "r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue
                if stripped.startswith("- "):
                    item = stripped[2:].strip().strip('"').strip("'")
                    current_list.append(item)
                elif ":" in stripped:
                    if current_key and current_list:
                        result[current_key] = current_list
                        current_list = []
                    key, val = stripped.split(":", 1)
                    key = key.strip()
                    val = val.strip().strip('"').strip("'")
                    if val == "":
                        current_key = key
                    else:
                        if val.isdigit():
                            val = int(val)
                        elif val.lower() == "true":
                            val = True
                        elif val.lower() == "false":
                            val = False
                        result[key] = val
                        current_key = None
            if current_key and current_list:
                result[current_key] = current_list
        return result

    @property
    def core_keywords(self):
        return [k.lower() for k in self.cfg.get("core_keywords", [])]

    @property
    def high_value_keywords(self):
        return [k.lower() for k in self.cfg.get("high_value_keywords", [])]

    @property
    def exclude_keywords(self):
        return [k.lower() for k in self.cfg.get("exclude_keywords", [])]

    @property
    def max_email_papers(self):
        return int(os.getenv("MAX_EMAIL_PAPERS", self.cfg.get("max_email_papers", 15)))

    @property
    def min_relevance_score(self):
        return int(os.getenv("MIN_RELEVANCE_SCORE", self.cfg.get("min_relevance_score", 5)))

    @property
    def lookback_days(self):
        return int(os.getenv("LOOKBACK_DAYS", self.cfg.get("lookback_days", 2)))

    def get_source_config(self, name):
        src = self.cfg.get("sources", {})
        if isinstance(src, dict):
            return src.get(name, {})
        return {}
