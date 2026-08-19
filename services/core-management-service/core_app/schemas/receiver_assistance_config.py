from __future__ import annotations

from pydantic import BaseModel, Field


class AssistanceDocumentSpecOut(BaseModel):
    type: str
    label: str
    required: bool = True
    condition: str | None = None


class ReceiverAssistanceCategoryOut(BaseModel):
    code: str
    name: str
    description: str
    requires_detailed_explanation: bool = True
    required_documents: list[AssistanceDocumentSpecOut] = Field(default_factory=list)
    optional_documents: list[AssistanceDocumentSpecOut] = Field(default_factory=list)
    conditional_documents: list[AssistanceDocumentSpecOut] = Field(default_factory=list)


class ReceiverAssistanceConfigOut(BaseModel):
    categories: list[ReceiverAssistanceCategoryOut]
    version: str = "1"
    limits: dict[str, float | int | str] | None = None
