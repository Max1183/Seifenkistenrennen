import datetime
import uuid
from typing import Optional

class ScanLogEntry:
    def __init__(self, start_nummer: str, status: str, scan_id: Optional[str] = None, timestamp_scan_lokal: Optional[datetime.datetime] = None, error_message: Optional[str] = None):
        self.scan_id = scan_id or str(uuid.uuid4())
        self.timestamp_scan_lokal = timestamp_scan_lokal or datetime.datetime.now()
        self.start_nummer = start_nummer
        self.status = status
        self.error_message = error_message

class MainDataEntry(dict): pass
class DisplayableMainData(dict): pass
