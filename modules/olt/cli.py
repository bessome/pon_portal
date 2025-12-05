"""CLI polling provider for OLT devices."""
from __future__ import annotations

from typing import Iterable

from . import ONURecord


def poll(olt: object) -> Iterable[ONURecord]:
    """Simulate CLI polling for a given OLT."""
    base_identifier = str(olt)
    records = []
    for index in range(1, 3):
        interface = f"gpon0/1/{index}"
        serial = f"CLI-{base_identifier}-{index}"
        status = "online"
        records.append(ONURecord(interface=interface, serial_number=serial, status=status))
    return records
