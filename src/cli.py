#!/usr/bin/env python3
"""Movie File Analyzer CLI - 하위 호환성을 위한 엔트리포인트."""

from __future__ import annotations

import sys
from pathlib import Path

# 프로젝트 루트를 PYTHONPATH에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.cli.main import main

if __name__ == "__main__":
    main()
