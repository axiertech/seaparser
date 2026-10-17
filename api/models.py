from typing import Literal
from pydantic import BaseModel,ConfigDict,Field,model_validator
from application.geographic_budget import validate_budget
from infrastructure.geography import to_local
from infrastructure.land import to_local as vinga_local


class Position(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True,allow_inf_nan=False)
    latitude: float
    longitude: float


class PlanInput(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True,allow_inf_nan=False)
    profile: Literal['synthetic','vinga']='vinga'
    start: Position
    target: Position
    margin_m: float=Field(default=2,ge=0,le=10)
    departure_offsets_seconds: list[int]=Field(default=[0,600],min_length=1,max_length=4)
    candidate_limit: int | None=Field(default=None,ge=2,le=8)
    scenario: Literal['baseline','weather-limit','unverified','missing-waves']='baseline'

    max_wind_m_s: float | None=Field(default=None,ge=0,le=100)
    max_wave_height_m: float | None=Field(default=None,ge=0,le=30)

    @model_validator(mode='after')
    def departures(self):
        if self.profile=='vinga' and self.scenario != 'baseline':
            raise ValueError('Vinga använder verkligt väder; syntetiska marina scenarier är bara referenstester')
        local=vinga_local if self.profile=='vinga' else to_local
        for p in (self.start,self.target):
            local(p.latitude,p.longitude)
        validate_budget(self.profile,self.candidate_limit,self.departure_offsets_seconds)
        return self
