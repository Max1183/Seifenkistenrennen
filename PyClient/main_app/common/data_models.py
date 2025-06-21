# --- START OF FILE main_app/common/data_models.py ---

from dataclasses import dataclass, field
from typing import Optional, Any, Dict
import datetime


# Die vollständige Definition für einen Rennfahrer
@dataclass
class Racer:
    start_number: str
    full_name: str
    soapbox_class_display: str = "N/A"  # Kistenklasse, mit Standardwert


# Die vollständige Definition für einen Renndurchlauf inkl. Metadaten
@dataclass
class RaceRun:
    app_item_id: str
    start_nummer: str
    round_number: str
    timestamp_messung: str

    # Optionale Felder mit Standardwerten
    renn_zeit: Optional[float] = None
    scan_id: Optional[str] = None
    zugeordneter_scan_id: Optional[str] = None
    disqualified: bool = False
    notes: Optional[str] = None

    # Metadaten für die App-Logik, werden meist automatisch gefüllt
    status: str = 'new'
    updated_at: str = field(default_factory=lambda: datetime.datetime.now().isoformat())
    _synced_to_website: bool = False
    original_data_snapshot: Optional[Dict[str, Any]] = None
    data_before_delete: Optional[Dict[str, Any]] = None

    def to_data_dict(self) -> Dict[str, Any]:
        """
        Wandelt die Kerndaten des Objekts in ein Dictionary um.
        Nützlich für Serialisierung, Snapshots oder das Senden an die API.
        """
        return {
            "start_nummer": self.start_nummer,
            "round_number": self.round_number,
            "renn_zeit": self.renn_zeit,
            "timestamp_messung": self.timestamp_messung,
            "scan_id": self.scan_id,
            "zugeordneter_scan_id": self.zugeordneter_scan_id,
            "disqualified": self.disqualified,
            "notes": self.notes,
            "updated_at": self.updated_at
        }


# Diese Klassen sind optional und können entfernt werden, wenn sie nicht anderweitig verwendet werden.
class MainDataEntry(dict):
    pass


class DisplayableMainData(dict):
    pass