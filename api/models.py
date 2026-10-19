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
    profile: Literal['synthetic','vinga','vinga-native','vinga-poc']='vinga'
    start: Position
    target: Position
    margin_m: float=Field(default=2,ge=0,le=10)
    departure_offsets_seconds: list[int]=Field(default=[0,600],min_length=1,max_length=4)
    candidate_limit: int | None=Field(default=None,ge=2,le=8)
    boat_profile: Literal['constant-5kn'] | None=None
    scenario: Literal['baseline','weather-limit','unverified','missing-waves']='baseline'

    max_wind_m_s: float | None=Field(default=None,ge=0,le=100)
    max_wave_height_m: float | None=Field(default=None,ge=0,le=30)

    @model_validator(mode='after')
    def departures(self):
        if self.profile in ('vinga','vinga-native','vinga-poc') and self.scenario != 'baseline':
            raise ValueError('Vinga använder verkligt väder; syntetiska marina scenarier är bara referenstester')
        from application.poc import local_position
        local=local_position if self.profile=='vinga-poc' else vinga_local if self.profile in ('vinga','vinga-native','vinga-poc') else to_local
        for p in (self.start,self.target):
            local(p.latitude,p.longitude)
        validate_budget(self.profile,self.candidate_limit,self.departure_offsets_seconds)
        return self


class CoastalPlanInput(BaseModel):
    """Server-owned regional bounds; clients cannot change search budgets."""
    model_config=ConfigDict(extra='forbid',strict=True,allow_inf_nan=False)
    start: Position
    target: Position
    departure: str
    boat_profile: Literal['constant-5kn']='constant-5kn'
    candidate_limit: int=Field(default=2,ge=1,le=2)
    max_wind_m_s: float=Field(default=18,ge=0,le=100)
    max_wave_height_m: float=Field(default=3,ge=0,le=30)

    @model_validator(mode='after')
    def regional_support(self):
        from application.coastal_presentation import coastal_coverage
        from datetime import datetime
        data=coastal_coverage();w,s,e,n=data['bbox']
        for p in (self.start,self.target):
            if not w<=p.longitude<=e or not s<=p.latitude<=n:
                raise ValueError('Start eller mål ligger utanför det markerade regionala prognosområdet')
        if self.start==self.target:raise ValueError('Välj olika start- och målpunkter')
        when=datetime.fromisoformat(self.departure.replace('Z','+00:00'))
        if when.tzinfo is None:raise ValueError('Avgången måste ha uttrycklig tidszon')
        first,last=(datetime.fromisoformat(data['valid_times'][i]) for i in (0,-1))
        if not first<=when<last:raise ValueError('Avgången ligger utanför gemensam giltighet för de frysta prognoserna')
        return self
