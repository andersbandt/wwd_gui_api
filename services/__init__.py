"""Per-equipment service classes that wrap raw drivers and expose high-level operations.

These services sit between the GUI tabs and the equipment drivers, providing
a clean API for connect/disconnect/operate workflows. The ClassController
owns these services, and tabs call service methods instead of reaching
through to raw driver APIs.

Usage (future):
    # In ClassController.__init__:
    self.ps_service = PSService(self)
    self.dmm_service = DMMService(self)

    # In a tab:
    result = self.cc.ps_service.connect(port, "SPD3303X")
    if result.success:
        self.labelIDValue.config(text=result.device_id)
"""

from services.equipment_service import EquipmentService, ConnectionResult
from services.dmm_service import DMMService
from services.ps_service import PSService
from services.fg_service import FGService
from services.osc_service import OscService
