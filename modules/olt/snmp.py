"""SNMP polling provider for OLT devices."""
from __future__ import annotations

import random
from typing import Iterable

from . import ONURecord


def poll(olt: object) -> Iterable[ONURecord]:
    """Simulate SNMP polling for a given OLT."""
    random.seed(str(olt))
    records: list[ONURecord] = []
    for index in range(1, 4):
        interface = f"pon-{index}"
        serial = f"SNMP-{index:02d}-{random.randint(1000, 9999)}"
        status = "online" if random.random() > 0.05 else "degraded"
        records.append(ONURecord(interface=interface, serial_number=serial, status=status))
    return records
