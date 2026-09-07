"""School calendar planning domain and solver."""

from .models import (
    Classroom,
    PlanningInput,
    PlanningSlot,
    Subject,
    Teacher,
    build_slots,
)
from .solver import Schedule, ScheduleError, solve

__all__ = [
    "Classroom",
    "PlanningInput",
    "PlanningSlot",
    "Schedule",
    "ScheduleError",
    "Subject",
    "Teacher",
    "build_slots",
    "solve",
]
