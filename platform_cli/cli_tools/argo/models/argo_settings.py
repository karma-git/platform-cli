from typing import Any, Optional

from pydantic import BaseModel


class ArgoConfigs(BaseModel):
    context: Optional[str] = None
    namespace: Optional[str] = None
    sync_app: Optional[str] = None
    sync: Optional[bool] = None
    no_sync: Optional[bool] = None
    verbose: Optional[str] = None
