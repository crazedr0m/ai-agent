# -*- coding: utf-8 -*-
# mcp_servers/code_analyzer/languages/php/__init__.py

from mcp_servers.code_analyzer.languages.php.analyzer import PhpAnalyzer  # noqa: F401
from mcp_servers.code_analyzer.languages.php.procedural import (  # noqa: F401
    analyze_procedural_file,
    scan_procedural_project,
)