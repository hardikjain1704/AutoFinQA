# custom_exception.py

import sys
import traceback
from typing import Optional, cast

class AutoFinQAException(Exception):
    """
    Custom exception class for the AutoFinQA project.
    It captures detailed context about the error, including the file name,
    line number, and a full traceback for easier debugging.
    """
    def __init__(self, error_message: object, error_details: Optional[object] = None):
        # Normalize the error message
        if isinstance(error_message, BaseException):
            norm_msg = str(error_message)
        else:
            norm_msg = str(error_message)
        
        # Resolve exception info (supports sys module, Exception Object, or current context)
        exc_type = exc_value = exc_tb = None
        if error_details is None:
            exc_type, exc_value, exc_tb = sys.exc_info()
        elif hasattr(error_details, "exc_info"):
            exc_info_obj = cast(sys, error_details)
            exc_type, exc_value, exc_tb = exc_info_obj.exc_info()
        elif isinstance(error_details, BaseException):
            exc_type, exc_value, exc_tb = type(error_details), error_details, error_details.__traceback__
        else:
            exc_type, exc_value, exc_tb = sys.exc_info()
        
        # Walk to the last frame of the report to get the most relevant location
        last_tb = exc_tb
        while last_tb and last_tb.tb_next:
            last_tb = last_tb.tb_next
        
        self.file_name = last_tb.tb_frame.f_code.co_filename if last_tb else '<unknown>'
        self.lineno = last_tb.tb_lineno if last_tb else -1
        self.error_message = norm_msg

        # Format the full traceback string
        if exc_type and exc_tb:
            self.traceback_str = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        else:
            self.traceback_str = "No traceback available."
        
        super().__init__(self.__str__())

    def __str__(self):
        """
        Returns a compact, logger-friendly message.
        """
        base = f"Error in [{self.file_name}] at line [{self.lineno}] | Message: {self.error_message}"
        return f"{base}\nTraceback:\n{self.traceback_str}"

    def __repr__(self):
        """
        Returns a developer-friendly representation of the exception.
        """
        return f"AutoFinQAException(file={self.file_name!r}, line={self.lineno}, message={self.error_message!r})"