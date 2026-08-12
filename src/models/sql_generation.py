from typing import Literal

from pydantic import BaseModel, Field, model_validator


class SQLGenerationResult(BaseModel):
    """Décision structurée produite par la chaîne Text-to-SQL."""

    status: Literal["ready", "clarification", "out_of_scope"]
    sql: str | None
    title: str
    interpretation: str
    clarification_question: str | None
    used_tables: list[str]
    applied_business_rules: list[str]
    confidence: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def validate_status_payload(self) -> "SQLGenerationResult":
        if self.status == "ready" and not (self.sql and self.sql.strip()):
            raise ValueError("sql est obligatoire lorsque status vaut ready")
        if self.status == "clarification" and not (
            self.clarification_question and self.clarification_question.strip()
        ):
            raise ValueError(
                "clarification_question est obligatoire lorsque status vaut clarification"
            )
        if self.status == "out_of_scope" and self.sql is not None:
            raise ValueError("sql doit être null lorsque status vaut out_of_scope")
        return self
