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
        
        exc_type, exc_value, exc_tb = None, None, None
        
        if error_details is None:
            # Case 1: No error_details, get current exception
            exc_type, exc_value, exc_tb = sys.exc_info()
            if exc_type is None:
                # Fallback if sys.exc_info() is empty
                try:
                    raise Exception("Fallback exception to capture stack")
                except Exception:
                    exc_type, exc_value, exc_tb = sys.exc_info()
        
        elif isinstance(error_details, BaseException):
            # Case 2: error_details is an exception object
            exc_value = error_details
            exc_type = type(exc_value)
            exc_tb = exc_value.__traceback__
        
        elif hasattr(error_details, "exc_info") and callable(error_details.exc_info):
            # Case 3: error_details is sys module
            exc_info_obj = cast(sys, error_details)
            exc_type, exc_value, exc_tb = exc_info_obj.exc_info()
            
        else:
            # Case 4: Fallback for other inputs, get current exception
            exc_type, exc_value, exc_tb = sys.exc_info()
            if exc_type is None:
                 try:
                    raise Exception("Fallback exception to capture stack")
                 except Exception:
                    exc_type, exc_value, exc_tb = sys.exc_info()

        # Walk to the last frame of the report to get the most relevant location
        last_tb = exc_tb
        if last_tb:
            while last_tb.tb_next:
                last_tb = last_tb.tb_next
        
        self.file_name = last_tb.tb_frame.f_code.co_filename if last_tb else '<unknown>'
        self.lineno = last_tb.tb_lineno if last_tb else -1
        self.error_message = norm_msg

        # Format the full traceback string
        if exc_type and exc_tb:
            # Use traceback.format_exception to correctly format
            self.traceback_str = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        elif isinstance(error_details, BaseException):
             self.traceback_str = "".join(traceback.format_exception(type(error_details), error_details, error_details.__traceback__))
        else:
            # Fallback if no traceback is found
            self.traceback_str = "".join(traceback.format_stack())
        # --- END OF UPDATE ---
        
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