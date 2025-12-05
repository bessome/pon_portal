"""Polling helpers for OLT devices."""
from dataclasses import dataclass


@dataclass
class ONURecord:
    """Normalized representation of an ONU entry."""

    interface: str
    serial_number: str
    status: str
