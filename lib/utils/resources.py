"""System-Ressourcen überwachen — bevor wir einen Browser starten."""
import os
import logging

log = logging.getLogger(__name__)

# Schwellwerte
MIN_FREE_RAM_MB   = 1200   # Minimum freier RAM für Browser-Start
MIN_FREE_DISK_MB  = 500    # Minimum freier /var-Space
MAX_LOAD_1MIN     = 3.5    # Maximale 1-Min-Load (4 Cores → 87%)


def free_ram_mb() -> int:
    """Freier + cached RAM in MB (aus /proc/meminfo)."""
    info = {}
    with open("/proc/meminfo") as f:
        for line in f:
            parts = line.split()
            if len(parts) >= 2:
                info[parts[0].rstrip(":")] = int(parts[1])
    # MemAvailable ist der realistische Wert für neue Prozesse
    return info.get("MemAvailable", 0) // 1024


def free_disk_mb(path: str = "/var") -> int:
    """Freier Disk-Space in MB."""
    st = os.statvfs(path)
    return (st.f_bavail * st.f_frsize) // (1024 * 1024)


def load_1min() -> float:
    """Aktuelle 1-Minuten-Systemlast."""
    return os.getloadavg()[0]


def can_start_browser() -> tuple[bool, str]:
    """
    Prüft ob genug Ressourcen für einen Browser-Start vorhanden.
    Gibt (ok, reason) zurück.
    """
    ram = free_ram_mb()
    if ram < MIN_FREE_RAM_MB:
        return False, f"RAM zu knapp: {ram}MB frei (Minimum {MIN_FREE_RAM_MB}MB)"

    disk = free_disk_mb("/var")
    if disk < MIN_FREE_DISK_MB:
        return False, f"/var Disk zu knapp: {disk}MB frei"

    load = load_1min()
    if load > MAX_LOAD_1MIN:
        return False, f"System überlastet: Load {load:.1f} (Max {MAX_LOAD_1MIN})"

    log.debug("Ressourcen OK — RAM %dMB, Disk %dMB, Load %.1f", ram, disk, load)
    return True, "ok"


def snapshot() -> dict:
    """Aktueller Ressourcen-Snapshot für Logs."""
    return {
        "ram_free_mb":  free_ram_mb(),
        "disk_free_mb": free_disk_mb("/var"),
        "load_1min":    round(load_1min(), 2),
    }
