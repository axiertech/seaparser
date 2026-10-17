"""Analytic physical-velocity vs projected-position integration references."""
import unittest
from datetime import datetime,timezone
from math import log
from prototype.calculation import sail_to_target,simulate
from prototype.model import Vector,ConstantBoat,KNOT
from prototype.environment import Conditions

T=datetime(2026,1,1,tzinfo=timezone.utc)


class AffineFrame:
    def evaluate(self,p,t):return Conditions(Vector(0,.6))
    def position_rate(self,p,v):return Vector(-3*v.north,2*v.east)
    def physical_direction(self,p,d):
        v=Vector(d.north/2,-d.east/3)
        return v.scaled(1/v.speed)


class MotionIntegrationTests(unittest.TestCase):
    def test_physical_speed_current_and_projected_distance_are_separate(self):
        voyage=sail_to_target(AffineFrame(),T,Vector(0,100),speed_knots=1/KNOT,
            step_seconds=20,tolerance_m=1e-6)
        self.assertEqual(voyage.status,'arrived')
        self.assertAlmostEqual(voyage.travel_seconds,62.5,delta=1e-5)
        for step in voyage.steps:
            self.assertAlmostEqual(step.midpoint.water.speed,1,places=12)
            self.assertAlmostEqual(step.midpoint.ground.east,.8,places=12)
            self.assertAlmostEqual(step.midpoint.ground.north,0,places=12)
            self.assertAlmostEqual(step.end_position.east,0,places=12)
        steps=simulate(ConstantBoat(1/KNOT,heading=90,leeway=0),AffineFrame(),T,10,step_seconds=5)
        self.assertAlmostEqual(steps[-1].end_position.east,-18,places=10)
        self.assertAlmostEqual(steps[-1].end_position.north,20,places=10)

    def test_position_dependent_midpoint_rate_converges_to_known_solution(self):
        class ExpFrame:
            def evaluate(self,p,t):return Conditions(Vector(0,0))
            def position_rate(self,p,v):return v.scaled(1+p.east/1000)
            def physical_direction(self,p,d):return d
        errors=[]
        for dt in (4,2):
            v=sail_to_target(ExpFrame(),T,Vector(100,0),speed_knots=1/KNOT,
                step_seconds=dt,tolerance_m=1e-7)
            self.assertEqual(v.status,'arrived')
            errors.append(abs(v.travel_seconds-1000*log(1.1)))
        self.assertLess(errors[1],errors[0]/3)

    def test_wind_current_and_boat_remain_in_physical_frame(self):
        case=self
        class WeatherFrame(AffineFrame):
            def evaluate(self,p,t):return Conditions(Vector(0,.6),wind=Vector(4,-3))
        class RecordingBoat(ConstantBoat):
            def compensate(self,direction,position,time,weather,min_progress_m_s):
                case.assertEqual(weather.wind,Vector(4,-3))
                case.assertEqual(weather.current,Vector(0,.6))
                case.assertEqual(weather.wind_reference,'ground')
                case.assertAlmostEqual(direction.east,1)
                case.assertAlmostEqual(direction.north,0)
                return super().compensate(direction,position,time,weather,min_progress_m_s)
        voyage=sail_to_target(WeatherFrame(),T,Vector(0,100),boat=RecordingBoat(1/KNOT),
                             step_seconds=10,tolerance_m=1e-6)
        self.assertEqual(voyage.status,'arrived')
        for step in voyage.steps:
            self.assertEqual(step.midpoint.wind,Vector(4,-3))
            self.assertEqual(step.midpoint.current,Vector(0,.6))
            self.assertAlmostEqual(step.midpoint.water.speed,1)

    def test_half_configured_motion_environment_is_rejected(self):
        class HalfFrame:
            def evaluate(self,p,t):return Conditions(Vector(0,0))
            def position_rate(self,p,v):return v
        with self.assertRaisesRegex(ValueError,'både'):
            sail_to_target(HalfFrame(),T,Vector(100,0))
