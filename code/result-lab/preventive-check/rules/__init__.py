from . import cluster_status
from . import cpu_core
from . import cpu_usage
from . import dev_stat
from . import disk_redundancy
from . import disk_stat
from . import disk_swap_usage
from . import filesystem_usage
from . import hba_connection_status
from . import inode_usage
from . import kernel_parameter
from . import memory_scan
from . import memory_usage
from . import network_link_status
from . import nic_redundancy_status
from . import paging_space
from . import path_redundancy_status
from . import ping_loss_status
from . import shared_volume_status
from . import system_log

RULES_MAP = {
    cluster_status.RULE_KEY: cluster_status.RULE_CLASS,
    cpu_core.RULE_KEY: cpu_core.RULE_CLASS,
    cpu_usage.RULE_KEY: cpu_usage.RULE_CLASS,
    dev_stat.RULE_KEY: dev_stat.RULE_CLASS,
    disk_redundancy.RULE_KEY: disk_redundancy.RULE_CLASS,
    disk_stat.RULE_KEY: disk_stat.RULE_CLASS,
    disk_swap_usage.RULE_KEY: disk_swap_usage.RULE_CLASS,
    filesystem_usage.RULE_KEY: filesystem_usage.RULE_CLASS,
    hba_connection_status.RULE_KEY: hba_connection_status.RULE_CLASS,
    inode_usage.RULE_KEY: inode_usage.RULE_CLASS,
    kernel_parameter.RULE_KEY: kernel_parameter.RULE_CLASS,
    memory_scan.RULE_KEY: memory_scan.RULE_CLASS,
    memory_usage.RULE_KEY: memory_usage.RULE_CLASS,
    network_link_status.RULE_KEY: network_link_status.RULE_CLASS,
    nic_redundancy_status.RULE_KEY: nic_redundancy_status.RULE_CLASS,
    paging_space.RULE_KEY: paging_space.RULE_CLASS,
    path_redundancy_status.RULE_KEY: path_redundancy_status.RULE_CLASS,
    ping_loss_status.RULE_KEY: ping_loss_status.RULE_CLASS,
    shared_volume_status.RULE_KEY: shared_volume_status.RULE_CLASS,
    system_log.RULE_KEY: system_log.RULE_CLASS,
}

__all__ = ["RULES_MAP"]
