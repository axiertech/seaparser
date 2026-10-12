from typing import Literal
from pydantic import BaseModel,ConfigDict,Field,model_validator
from infrastructure.geography import to_local
from infrastructure.land import to_local as vinga_local


class Position(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True,allow_inf_nan=False)
    latitude: float
    longitude: float


class PlanInput(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True,allow_inf_nan=False)
    profile: Literal['synthetic','vinga']='synthetic'
    start: Position
    target: Position
    margin_m: float=Field(default=2,ge=0,le=10)
    departure_offsets_seconds: list[int]=Field(default=[0,600],min_length=1,max_length=2)
    scenario: Literal['baseline','weather-limit','unverified','missing-waves']='baseline'

    @model_validator(mode='after')
    def departures(self):
        local=vinga_local if self.profile=='vinga' else to_local
        for p in (self.start,self.target):
            local(p.latitude,p.longitude)
        if any(o not in (0,600) for o in self.departure_offsets_seconds) or len(set(self.departure_offsets_seconds)) != len(self.departure_offsets_seconds):
            raise ValueError('Unika syntetiska avgångsoffset 0 eller 600 krävs')
        return self
