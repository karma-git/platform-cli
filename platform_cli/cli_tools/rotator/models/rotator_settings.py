from typing import Any, Optional

from pydantic import BaseModel


class RotatorConfigs(BaseModel):
    context: Optional[str] = None
    selector: Optional[str] = None
    mode: Optional[str] = None
    sleep: Optional[str] = None
    ratio: Optional[str] = None
    verbose: Optional[str] = None
