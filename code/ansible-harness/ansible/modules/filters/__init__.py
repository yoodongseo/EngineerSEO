from .base_filter import BaseFilter
from .cpu_filter import CPUFilter
from .memory_filter import MemoryFilter
from .disk_filter import DiskFilter
from .path_filter import PathFilter
from .file_permissions_filter import CriticalFilePermissionFilter
from .suid_sgid_filter import SUIDSGIDFilter
from .inactive_account_lock_filter import InactiveAccountLockFilter
from .world_writable_filter import WorldWritableFileFilter
from .finger_disable_filter import FingerServiceFilter
from .telnet_disable_filter import TelnetServiceFilter
from .r_service_disable_filter import RServiceFilter
#from .messages_filter import MessagesFilter
from .chronyd_filter import ChronydFilter
from .ntp_filter import NtpFilter
from .fan_filter import FanFilter
from .pg_space import PgspaceFilter
from .dev_scan import DevscanFilter
from .swap_util import SwapFilter
from .inode_filter import InodeFilter
from .log_filter import LogFilter
from .kernel_filter import KernelFilter
from .redundancy_filter import RedundancyFilter
from .cluster_filter import ClusterFilter
from .shared_volume_filter import SharedVolumeFilter
from .network_filter import NetworkFilter
from .pingloss_filter import PingLossFilter
from .aix_network_link_filter import AixNetworkLinkFilter
from .hpux_path_redundancy_filter import HPUXPathRedundancyFilter
from .aix_redundancy_filter import AixRedundancyFilter
from .aix_pingloss_filter import AixPingLossFilter
from .hpux_hba_status_filter import HPUXHbaStatusFilter
from .aix_path_filter import AixPathFilter
from .aix_hba_filter import AixHbaFilter
from .rhel6_hba_status_filter import RHEL6HbaStatusFilter
from .rhel6_path_redundancy_filter import RHEL6PathRedundancyFilter
from .rhel6_pingloss_filter import RHEL6PingLossFilter
from .rhel6_swap_fileter import Rhel6SwapFilter
from .rhel6_redundancy_filter import RHEL6RedundancyFilter
from .rhel6_network_link_filter import RHEL6NetworkLinkFilter
from .rhel6_shared_volume_filter import RHEL6SharedVolumeFilter
from .rhel6_inode_filter import Rhel6InodeFilter
from .rhel6_cluster_filter import RHEL6ClusterFilter
from .sun_hba_status_filter import SunHbaStatusFilter
from .sun_cpu_filter import SunCPUFilter
from .sun_cpuinfo_filter import SunCPUInfoFilter
from .sun_path_redundancy_filter import SunPathRedundancyFilter
from .sun_pingloss_filter import SunPingLossFilter
from .sun_redundancy_filter import SunRedundancyFilter
from .sun_network_link_filter import SunNetworkLinkFilter
from .sun_memory_filter import SunMemoryFilter
from .sun_shared_volume_filter import SunSharedVolumeFilter
from .sun_disk_filter import SunDiskFilter
from .sun_cluster_filter import SunClusterFilter
from .sun_inode_filter import SunInodeFilter
from .process_filter import ProcessFilter
from .stat_filter import StatFilter
from .jmap_heap_filter import JampHeapFilter
from .jcmd_filter import JcmdFilter
from .windows_filter import *
from .oracle_resource_filter import OracleResourceFilter
from .oracle_access_filter import OracleAccessFilter
from .oracle_process_limit_filter import OracleProcessLimitFilter
from .oracle_sga_filter import OracleSgaFilter
from .oracle_redundancy_filter import OracleRedundancyFilter
from .oracle_controlfile_filter import OracleControlfileFilter
from .oracle_redolog_filter import OracleRedologFilter
from .oracle_logfile_filter import OracleLogfileFilter
from .oracle_spfile_backup_filter import OracleSpfileBackupFilter
from .oracle_tablespace_filter import OracleTablespaceFilter
from .oracle_backup_filter import OracleBackupFilter
from .oracle_backupcheck_filter import OracleBackupCheckFilter
from .mongodb_json_filter import MongodbJsonFilter
from .timedatectl_filter import TimedatectlFilter
from .ps_percent_filter import PsPercentFilter

filter_registry = {
    "cpustatfilter": CPUFilter,
    "memstatfilter": MemoryFilter,
    "diskstatfilter": DiskFilter,
    "path": PathFilter,
    "criticalfilepermission": CriticalFilePermissionFilter,
    "suidsgid": SUIDSGIDFilter,
    "inactiveaccountlock": InactiveAccountLockFilter,
    "worldwritablefile": WorldWritableFileFilter,
    "fingerservice": FingerServiceFilter,
    "telnet": TelnetServiceFilter,
    "rservice": RServiceFilter,
#    "messages": MessagesFilter,
    "chronyd": ChronydFilter,
    "ntp": NtpFilter,
    "fan": FanFilter,
    "pagingspacefilter": PgspaceFilter,
    "devstatfilter": DevscanFilter,
    "swapstatfilter": SwapFilter,
    "inodefilter": InodeFilter,
    "logfilter": LogFilter,
    "kernelfilter": KernelFilter,
    "redundancyfilter": RedundancyFilter,
    "clusterfilter": ClusterFilter,
    "sharedvolumefilter": SharedVolumeFilter,
    "networkfilter": NetworkFilter,
    "pinglossfilter": PingLossFilter,
    "AixNetworkLinkFilter": AixNetworkLinkFilter,
    "AixRedundancyFilter": AixRedundancyFilter,
    "HPUXPathRedundancyFilter": HPUXPathRedundancyFilter,
    "AixPingLossFilter": AixPingLossFilter,
    "HPUXHbaStatusFilter": HPUXHbaStatusFilter,
    "AixPathFilter": AixPathFilter,
    "AixHbaFilter": AixHbaFilter,
    "RHEL6HbaStatusFilter": RHEL6HbaStatusFilter,
    "RHEL6PathRedundancyFilter": RHEL6PathRedundancyFilter,
    "RHEL6PingLossFilter": RHEL6PingLossFilter,
    "Rhel6SwapFilter": Rhel6SwapFilter,
    "RHEL6RedundancyFilter": RHEL6RedundancyFilter,
    "RHEL6NetworkLinkFilter": RHEL6NetworkLinkFilter,
    "RHEL6SharedVolumeFilter": RHEL6SharedVolumeFilter,
    "Rhel6InodeFilter": Rhel6InodeFilter,
    "RHEL6ClusterFilter": RHEL6ClusterFilter,
    "SunHbaStatusFilter": SunHbaStatusFilter,
    "SunCPUFilter": SunCPUFilter,
    "SunCPUInfoFilter": SunCPUInfoFilter,
    "SunPathRedundancyFilter": SunPathRedundancyFilter,
    "SunPingLossFilter": SunPingLossFilter,
    "SunRedundancyFilter": SunRedundancyFilter,
    "SunNetworkLinkFilter": SunNetworkLinkFilter,
    "SunMemoryFilter": SunMemoryFilter,
    "SunSharedVolumeFilter": SunSharedVolumeFilter,
    "SunDiskFilter": SunDiskFilter, 
    "SunClusterFilter": SunClusterFilter,
    "SunInodeFilter": SunInodeFilter,
    "ProcessFilter": ProcessFilter,
    "StatFilter": StatFilter,
    "JampHeapFilter": JampHeapFilter,
    "JcmdFilter": JcmdFilter,
###############################   [WINDOWS FILTER ZONE] (행안부 기준) (필수 14 권고 1)   ###############################


# 성능/자원
    "winMpstatEquivalentCpuFilter": winMpstatEquivalentCpuFilter,
    "winFreeMemoryFilter": winFreeMemoryFilter,
    "winFreeSwapFilter": winFreeSwapFilter,
    "winPagingSpaceFilter": winPagingSpaceFilter,
    "winFilesystemUsageFilter": winFilesystemUsageFilter,
    "winDiskSwapUsageFilter": winDiskSwapUsageFilter,

    # 이벤트 로그(System/Clustering)
    "winLogSystemAnomalyFilter": winLogSystemAnomalyFilter,
    "winLogKernelPanicFilter": winLogKernelPanicFilter,
    "winLogCpuEccErrorFilter": winLogCpuEccErrorFilter,
    "winLogMemoryEccErrorFilter": winLogMemoryEccErrorFilter,
    "winLogFanFailFilter": winLogFanFailFilter,
    "winLogPowerPsuFailFilter": winLogPowerPsuFailFilter,
    "winLogHbaAnomalyFilter": winLogHbaAnomalyFilter,
    "winLogNicAnomalyFilter": winLogNicAnomalyFilter,
    "winLogIoErrorFilter": winLogIoErrorFilter,
    "winLogClusterStatusChangeFilter": winLogClusterStatusChangeFilter,

    # 네트워크
    "winNicLinkStateSpeedFilter": winNicLinkStateSpeedFilter,

###########################################################################################################################
    "OracleResourceFilter": OracleResourceFilter,
    "OracleAccessFilter": OracleAccessFilter,
    "OracleProcessLimitFilter": OracleProcessLimitFilter,
    "OracleSgaFilter": OracleSgaFilter,
    "OracleRedundancyFilter": OracleRedundancyFilter,
    "OracleControlfileFilter": OracleControlfileFilter,
    "OracleRedologFilter": OracleRedologFilter,
    "OracleLogfileFilter": OracleLogfileFilter,
    "OracleSpfileBackupFilter": OracleSpfileBackupFilter,
    "OracleTablespaceFilter": OracleTablespaceFilter,
    "OracleBackupFilter": OracleBackupFilter,
    "OracleBackupCheckFilter": OracleBackupCheckFilter,
    "MongodbJsonFilter": MongodbJsonFilter,
    "TimedatectlFilter": TimedatectlFilter,
    "PsPercentFilter": PsPercentFilter,
}
