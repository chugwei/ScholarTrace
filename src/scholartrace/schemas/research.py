"""Research-question contracts."""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

NonBlankText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
RequiredTextList = Annotated[list[NonBlankText], Field(min_length=1)]


class ResearchQuestion(BaseModel):
    """A testable research question with explicit unknowns and constraints."""

    model_config = ConfigDict(extra="forbid")

    problem: NonBlankText
    target_population_or_domain: NonBlankText
    inputs: RequiredTextList
    expected_outputs: RequiredTextList
    constraints: list[NonBlankText]
    success_criteria: RequiredTextList
    assumptions: list[NonBlankText]
    unresolved_questions: list[NonBlankText]
