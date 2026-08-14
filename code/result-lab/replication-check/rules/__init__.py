from .rep_hpe import HPERemoteCopyRule
from .rep_ibm import IBMRemoteCopyRule
from .rep_netapp import NetAppSnapMirrorRule

RULES_MAP = {
    NetAppSnapMirrorRule.RULE_KEY: NetAppSnapMirrorRule,
    HPERemoteCopyRule.RULE_KEY: HPERemoteCopyRule,
    IBMRemoteCopyRule.RULE_KEY: IBMRemoteCopyRule,
}

__all__ = [
    "HPERemoteCopyRule",
    "IBMRemoteCopyRule",
    "NetAppSnapMirrorRule",
    "RULES_MAP",
]
