"""C-02 authorization public interface (re-exported for convenience)."""
from .service import (  # noqa: F401
    EXTERNAL,
    GLOBAL_ROLES,
    authorize,
    can_read,
    external_student_view,
    subject,
    visible_placement_ids,
)
