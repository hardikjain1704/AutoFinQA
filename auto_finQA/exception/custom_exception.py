import sys
import traceback
from typing import Optional, cast

class CustomException(Exception):
    def __init__(self, error_message, error_details: Optional[object] = None):
        pass

    def __str__(self):
        pass

    def __repr__(self):
        pass
