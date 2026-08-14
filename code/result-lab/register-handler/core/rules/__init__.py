try:
    from .preventive import RULES_MAP as PREVENTIVE_RULES_MAP
except ImportError:
    PREVENTIVE_RULES_MAP = {}

try:
    from .security import RULES_MAP as SECURITY_RULES_MAP
except ImportError:
    SECURITY_RULES_MAP = {}

try:
    from .replication import RULES_MAP as REPLICATION_RULES_MAP
except ImportError:
    REPLICATION_RULES_MAP = {}

RULES_MAP = {}
RULES_MAP.update(PREVENTIVE_RULES_MAP)
RULES_MAP.update(SECURITY_RULES_MAP)
RULES_MAP.update(REPLICATION_RULES_MAP)


def get_rules_map(report_type=""):
    normalized = str(report_type or "").strip().lower()
    if normalized == "security":
        return SECURITY_RULES_MAP
    if normalized in ("replication", "replicationstatus"):
        return REPLICATION_RULES_MAP
    if normalized in ("", "preventive", "prevention"):
        return PREVENTIVE_RULES_MAP
    return RULES_MAP


__all__ = [
    "PREVENTIVE_RULES_MAP",
    "SECURITY_RULES_MAP",
    "REPLICATION_RULES_MAP",
    "RULES_MAP",
    "get_rules_map",
]
