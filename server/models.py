from pydantic import BaseModel, Field
from typing import List, Optional

class TranscriptSegment(BaseModel):
    text: str
    start: float
    duration: float

    @property
    def end(self) -> float:
        return self.start + self.duration

class ViralMoment(BaseModel):
    title: str = Field(description="Punchy, click-worthy title for the reel")
    hook: str = Field(description="The opening hook / text overlay (max 8 words, high curiosity)")
    start_time: float = Field(description="Start time in seconds")
    end_time: float = Field(description="End time in seconds")
    duration: float = Field(description="Total duration in seconds")
    viral_score: int = Field(description="Viral potential score from 1 to 100")
    reason: str = Field(description="Why this specific clip will hold retention and go viral")
    key_quote: str = Field(description="The most memorable or controversial quote in the clip")

class AnalysisResponse(BaseModel):
    video_summary: str = Field(description="Brief summary of the video content")
    viral_moments: List[ViralMoment] = Field(description="List of selected viral segments ranked by viral score")
