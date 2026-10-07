from pydantic import BaseModel, Field


class CriticScoreSummary(BaseModel):
    score: int | None = None
    review_count: int | None = Field(default=None, alias="reviewCount")
    positive_count: int | None = Field(default=None, alias="positiveCount")
    neutral_count: int | None = Field(default=None, alias="neutralCount")
    negative_count: int | None = Field(default=None, alias="negativeCount")


class Season(BaseModel):
    id: int
    title: str

    season_number: int = Field(alias="seasonNumber")
    season_slug: str | None = Field(default=None, alias="seasonSlug")
    premiere_date: str | None = Field(default=None, alias="premiereDate")

    critic_score_summary: CriticScoreSummary | None = Field(
        default=None,
        alias="criticScoreSummary",
    )


class Show(BaseModel):
    id: int
    title: str
    slug: str
    premiere_year: int | None = Field(default=None, alias="premiereYear")


class FinderData(BaseModel):
    items: list[Show]
    total_results: int = Field(alias="totalResults")


class FinderResponse(BaseModel):
    data: FinderData


class SeasonListData(BaseModel):
    items: list[Season]


class SeasonListResponse(BaseModel):
    data: SeasonListData