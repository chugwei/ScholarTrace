"""Research-question contracts."""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from scholartrace.identifiers import IDENTIFIER_PATTERN

NonBlankText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
RequiredTextList = Annotated[list[NonBlankText], Field(min_length=1)]
#: Request-field text bound to the canonical identifier pattern. Using it on
#: API request models makes malformed identifiers fail as 422 at the boundary
#: instead of surfacing as repository ValueError/500.
IdentifierText = Annotated[
    str, StringConstraints(strip_whitespace=True, pattern=IDENTIFIER_PATTERN)
]


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
