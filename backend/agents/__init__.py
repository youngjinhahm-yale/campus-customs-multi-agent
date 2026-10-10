"""The five Campus Customs agent roles."""

from . import accounting, boss, customer_service, facilities, inventory
from .spec import AgentSpec

SPECS: dict[str, AgentSpec] = {
    m.SPEC.name: m.SPEC for m in (boss, inventory, accounting, facilities, customer_service)
}
