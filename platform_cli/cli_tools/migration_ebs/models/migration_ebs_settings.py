from typing import Any, Optional

from pydantic import BaseModel


class MigrationEbsConfigs(BaseModel):
    context: Optional[str] = None
    namespace: Optional[str] = None
    pvc: Optional[str] = None
    sc: Optional[str] = None
    sync_app: Optional[str] = None
    vs: Optional[str] = None
    verbose: Optional[str] = None
