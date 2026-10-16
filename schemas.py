from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

EM_DASH = "\u2014"


class EmailDraft(BaseModel):
    subject: str = Field(min_length=3, max_length=100)
    body: str = Field(min_length=40, max_length=1800)

    @field_validator("subject", "body")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        # Defensive cleanup even though the prompt forbids em dashes.
        return value.replace(EM_DASH, "-").strip()

    @field_validator("subject")
    @classmethod
    def reject_header_injection(cls, value: str) -> str:
        if "\r" in value or "\n" in value:
            raise ValueError("Subject cannot contain line breaks.")
        return value

    @field_validator("body")
    @classmethod
    def keep_body_concise(cls, value: str) -> str:
        word_count = len(value.split())
        if not 60 <= word_count <= 155:
            raise ValueError("Email body must contain between 60 and 155 words.")
        return value
