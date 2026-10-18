import unittest
from datetime import datetime,timedelta,timezone
import numpy as np
from shapely import box,to_wkb,unary_union
from infrastructure.coastal_water import CoastalWater
from infrastructure.marine_reserve import MarineReserve,ReservePolicy
from infrastructure.land import FORWARD
from prototype.forecast_data import DataUnavailable
from prototype.model import Vector

START=datetime(2026,10,18,9,tzinfo=timezone.utc)

class MarineReserveTests(unittest.TestCase):
    def make(self,water,policy=None):
        values=np.zeros((2,2,2,2));values[:,:,:,0]=[[1,9],[1,9]]
        return MarineReserve('current',[11.58,11.62],[57.633,57.64],[START,START+timedelta(hours=1)],values,water,
            {v:policy or ReservePolicy() for v in ('current_east_m_s','current_north_m_s')})
    def test_nearest_node_across_land_is_rejected_for_farther_same_water_source(self):
        water=CoastalWater(to_wkb(unary_union([box(-10000,-10000,500,10000),box(800,-10000,10000,10000)])),'test')
        field=self.make(water);point=Vector(*FORWARD.transform(11.61,57.6334));value,records=field.sample(point,START)
        self.assertEqual(value,(1.,0.));self.assertEqual(len(records),2)
        self.assertTrue(all(r.source_longitude==11.58 and r.distance_m>1500 and r.time_offset_seconds==0 and r.uncertainty=='high' for r in records))
        self.assertEqual(records[0].source_value,1);self.assertEqual(records[1].source_value,0)
    def test_complete_native_interpolation_is_not_marked_as_reserve(self):
        water=CoastalWater(to_wkb(box(-10000,-10000,10000,10000)),'test');field=self.make(water)
        value,records=field.sample(Vector(*FORWARD.transform(11.60,57.6365)),START+timedelta(minutes=30))
        self.assertAlmostEqual(value[0],5,delta=1e-6);self.assertEqual(value[1],0);self.assertEqual(records,())
    def test_temporal_estimate_records_signed_offset_and_cannot_exceed_configured_limit(self):
        water=CoastalWater(to_wkb(box(-10000,-10000,10000,10000)),'test');field=self.make(water,ReservePolicy(max_time_offset_seconds=3600))
        _,records=field.sample(Vector(*FORWARD.transform(11.60,57.6365)),START+timedelta(hours=2))
        self.assertTrue(all(r.source_time==START+timedelta(hours=1) and r.time_offset_seconds==-3600 for r in records))
        with self.assertRaises(DataUnavailable):field.sample(Vector(*FORWARD.transform(11.60,57.6365)),START+timedelta(hours=3))
    def test_disabled_or_empty_reserve_does_not_fill_with_zero(self):
        water=CoastalWater(to_wkb(unary_union([box(-10000,-10000,500,10000),box(800,-10000,10000,10000)])),'test')
        point=Vector(*FORWARD.transform(11.61,57.6334))
        for policy in (ReservePolicy(method='none'),ReservePolicy(max_distance_m=1000)):
            with self.assertRaises(DataUnavailable):self.make(water,policy).sample(point,START)

    def test_invalid_source_value_cannot_be_reclassified_as_a_reservable_gap(self):
        water=CoastalWater(to_wkb(box(-10000,-10000,10000,10000)),'test')
        policies={v:ReservePolicy() for v in ('wave_height_m','wave_period_seconds','wave_direction_from_degrees')}
        for height,period in ((-1,np.nan),(np.nan,0),(np.inf,4)):
            values=np.full((2,2,2,4),np.nan);values[0,0,0]=[height,period,0,1]
            with self.subTest(height=height,period=period),self.assertRaises(ValueError):
                MarineReserve('waves',[11.58,11.62],[57.633,57.64],[START,START+timedelta(hours=1)],values,water,policies)

    def test_wave_direction_interpolates_across_north_and_real_zero_height_survives(self):
        water=CoastalWater(to_wkb(box(-10000,-10000,10000,10000)),'test')
        from infrastructure.copernicus_fields import wave_node
        values=np.array([[[wave_node(0,4,359,1),wave_node(0,4,1,1)]]*2]*2)
        policies={v:ReservePolicy() for v in ('wave_height_m','wave_period_seconds','wave_direction_from_degrees')}
        field=MarineReserve('waves',[11.58,11.62],[57.633,57.64],[START,START+timedelta(hours=1)],values,water,policies)
        value,records=field.sample(Vector(*FORWARD.transform(11.60,57.6365)),START+timedelta(minutes=30))
        self.assertEqual(value[:2],(0.,4.));self.assertAlmostEqual(value[2],0,delta=1e-12);self.assertGreater(value[3],.999)
        self.assertEqual(records,())

    def test_product_obeys_each_variable_policy_without_mixing_source_states(self):
        water=CoastalWater(to_wkb(unary_union([box(-10000,-10000,500,10000),box(800,-10000,10000,10000)])),'test')
        field=self.make(water);values=field.values
        policies={'current_east_m_s':ReservePolicy(max_distance_m=20000),
                  'current_north_m_s':ReservePolicy(max_distance_m=1000)}
        field=MarineReserve('current',field.longitude,field.latitude,field.times,values,water,policies)
        with self.assertRaises(DataUnavailable):field.sample(Vector(*FORWARD.transform(11.61,57.6334)),START)

    def test_wind_reserve_source_position_belongs_to_the_actual_native_grid(self):
        from pathlib import Path
        from scripts.regional_forecast import load_native_wind
        from infrastructure.marine_reserve import NativeWindWithReserve
        from infrastructure.met_wind_segments import MET_FORWARD
        sample=load_native_wind(Path(__file__).resolve().parents[1]/'fixtures')
        water=CoastalWater(to_wkb(box(-10000,-10000,10000,10000)),'test')
        field=NativeWindWithReserve(sample,water,{v:ReservePolicy() for v in ('wind_east_m_s','wind_north_m_s')})
        when=sample.times[-1]+timedelta(hours=1)
        _,records=field.sample(Vector(500,350),when)
        self.assertEqual(len(records),2)
        x,y=MET_FORWARD.transform(records[0].source_longitude,records[0].source_latitude)
        self.assertLess(min(abs(float(v)-x) for v in sample.x_m),1e-6)
        self.assertLess(min(abs(float(v)-y) for v in sample.y_m),1e-6)
        self.assertEqual(records[0].source_time,sample.times[-1])
        self.assertEqual(records[0].time_offset_seconds,-3600)
