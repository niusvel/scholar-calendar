"""Explain proven scheduling conflicts using named mandatory constraints."""

from dataclasses import dataclass
from time import monotonic

from ortools.sat.python import cp_model


@dataclass(frozen=True)
class ConfigurationConflict:
    title: str
    detail: str
    section: str


class DiagnosticRules:
    """Guard rule groups only in the diagnostic model; normal solving is unchanged."""

    def __init__(self, model: cp_model.CpModel, enabled: bool = False) -> None:
        self.model = model
        self.enabled = enabled
        self.literals = {}
        self.conflicts: dict[int, ConfigurationConflict] = {}

    def literal(self, key: tuple, title: str, detail: str, section: str):
        if key not in self.literals:
            literal = self.model.NewBoolVar(f"rule_{len(self.literals)}")
            self.literals[key] = literal
            self.conflicts[literal.Index()] = ConfigurationConflict(title, detail, section)
            self.model.AddAssumption(literal)
        return self.literals[key]

    def enforce(self, constraint, key: tuple, title: str, detail: str, section: str) -> None:
        if self.enabled:
            constraint.OnlyEnforceIf(self.literal(key, title, detail, section))

    def explain(self, time_limit: float = 10) -> tuple[ConfigurationConflict, ...]:
        """Return a proven sufficient conflict, reducing it while time remains.

        Unchecked removals are never accepted. This is not guaranteed to be the
        smallest conflict, nor to describe every independent conflict in a center.
        """
        solver = cp_model.CpSolver()
        solver.parameters.num_search_workers = 1
        deadline = monotonic() + time_limit
        solver.parameters.max_time_in_seconds = max(0.001, time_limit / 2)
        if solver.Solve(self.model) != cp_model.INFEASIBLE:
            return ()
        core = list(solver.SufficientAssumptionsForInfeasibility())
        if not core or any(index not in self.conflicts for index in core):
            return ()
        literals = {literal.Index(): literal for literal in self.literals.values()}
        for index in tuple(core):
            remaining = deadline - monotonic()
            if remaining <= 0:
                break
            trial = [item for item in core if item != index]
            self.model.ClearAssumptions()
            self.model.AddAssumptions(literals[item] for item in trial)
            solver.parameters.max_time_in_seconds = min(1, remaining)
            if solver.Solve(self.model) == cp_model.INFEASIBLE:
                core = trial
        return tuple(self.conflicts[index] for index in sorted(core))
