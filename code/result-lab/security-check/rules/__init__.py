from . import sec_account_separation
from . import sec_default_account
from . import sec_directed_broadcast
from . import sec_mask_reply
from . import sec_password_setting
from . import sec_plain_service
from . import sec_ransomware_port
from . import sec_remote_access
from . import sec_source_routing
from . import sec_unused_interface
from . import sec_srv_account_separation
from . import sec_srv_default_account
from . import sec_srv_default_port
from . import sec_srv_etc_port
from . import sec_srv_log_retention
from . import sec_srv_password_policy
from . import sec_srv_plain_port

RULES_MAP = {
    sec_account_separation.RULE_KEY: sec_account_separation.RULE_CLASS,
    sec_default_account.RULE_KEY: sec_default_account.RULE_CLASS,
    sec_directed_broadcast.RULE_KEY: sec_directed_broadcast.RULE_CLASS,
    sec_mask_reply.RULE_KEY: sec_mask_reply.RULE_CLASS,
    sec_password_setting.RULE_KEY: sec_password_setting.RULE_CLASS,
    sec_plain_service.RULE_KEY: sec_plain_service.RULE_CLASS,
    sec_ransomware_port.RULE_KEY: sec_ransomware_port.RULE_CLASS,
    sec_remote_access.RULE_KEY: sec_remote_access.RULE_CLASS,
    sec_source_routing.RULE_KEY: sec_source_routing.RULE_CLASS,
    sec_unused_interface.RULE_KEY: sec_unused_interface.RULE_CLASS,
    sec_srv_account_separation.RULE_KEY: sec_srv_account_separation.RULE_CLASS,
    sec_srv_default_account.RULE_KEY: sec_srv_default_account.RULE_CLASS,
    sec_srv_default_port.RULE_KEY: sec_srv_default_port.RULE_CLASS,
    sec_srv_etc_port.RULE_KEY: sec_srv_etc_port.RULE_CLASS,
    sec_srv_log_retention.RULE_KEY: sec_srv_log_retention.RULE_CLASS,
    sec_srv_password_policy.RULE_KEY: sec_srv_password_policy.RULE_CLASS,
    sec_srv_plain_port.RULE_KEY: sec_srv_plain_port.RULE_CLASS,
}

__all__ = ["RULES_MAP"]
