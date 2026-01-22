from sqlalchemy.orm import DeclarativeBase
import sys
from typing import Union

# Monkey patch for SQLAlchemy 2.0.46 Python 3.14 compatibility
# Fixes: TypeError: descriptor '__getitem__' requires a 'typing.Union' object but received a 'tuple'
if sys.version_info >= (3, 14):
    import sqlalchemy.util.typing as sa_typing
    
    # Store original function
    _original_make_union_type = sa_typing.make_union_type
    
    # Create patched version
    def _patched_make_union_type(*types):
        """Patched version for Python 3.14 compatibility"""
        # In Python 3.14, Union needs to be called with unpacked arguments
        if len(types) == 1:
            return types[0]
        # Use Union with unpacked types - Python 3.14 requires this syntax
        return Union[*types]
    
    # Apply patch
    sa_typing.make_union_type = _patched_make_union_type

class Base(DeclarativeBase):
    pass
