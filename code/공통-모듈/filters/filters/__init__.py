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
from .log_filter import LogFilter
from .network_filter import NetworkFilter


filter_registry = {
    "cpu": CPUFilter,
    "memory": MemoryFilter,
    "disk": DiskFilter,
    "path": PathFilter,
    "criticalfilepermission": CriticalFilePermissionFilter,
    "suidsgid": SUIDSGIDFilter,
    "inactiveaccountlock": InactiveAccountLockFilter,
    "worldwritablefile": WorldWritableFileFilter,
    "fingerservice": FingerServiceFilter,
    "telnet": TelnetServiceFilter,
    "rservice": RServiceFilter,
    "Log": LogFilter,
    "network": NetworkFilter
}
