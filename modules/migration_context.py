# -*- coding: utf-8 -*-
# modules/migration_context.py — Facade: реэкспорт из модульных файлов (Фаза 6.3/6.4)
#
# После рефакторинга:
#   checkpoint_manager.py — CheckpointManager, generate_migration_report
#   progress_reporter.py  — ProgressReporter
#   log16_integration.py  — LOG16Integration

from modules.checkpoint_manager import CheckpointManager, DEFAULT_CHECKPOINT_DIR, generate_migration_report  # noqa: F401
from modules.progress_reporter import ProgressReporter  # noqa: F401
from modules.log16_integration import LOG16Integration  # noqa: F401