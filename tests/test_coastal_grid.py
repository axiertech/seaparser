"""Exact grid acceleration must retain boundaries, search results and budgets."""
import tempfile
import unittest
from copy import deepcopy
from unittest.mock import patch

from shapely import box,to_wkb
from infrastructure.coastal_water import CoastalWater
from infrastructure.coastal_grid import CoastalGrid,build_grid,attach_grid
from prototype.model import Vector
from prototype.water_routing import generate_water_routes


class CoastalGridTests(unittest.TestCase):
    def test_invalid_cached_geometry_and_build_arguments_are_rejected(self):
        water,_=self.waters();data=build_grid(water)
        for changes in ({'spacing_m':0},{'spacing_m':True},{'spacing_m':float('nan')},
                        {'margin_m':-1},{'margin_m':True},{'shape':[True,5]},
                        {'shape':[1001,1000]},{'origin':[0.5,0]},{'flags':'gA=='}):
            with self.subTest(changes=changes),self.assertRaises(ValueError):CoastalGrid({**deepcopy(data),**changes})
        for changes in ({'spacing_m':True},{'margin_m':float('nan')},{'margin_m':True}):
            with self.subTest(changes=changes),self.assertRaises(ValueError):build_grid(water,**changes)
    def waters(self):
        data=to_wkb(box(-100,-100,1100,1100).difference(box(100,-50,110,50)))
        return CoastalWater(data,'known-thin-island'),CoastalWater(data,'known-thin-island')

    def test_every_point_and_eight_neighbour_edge_matches_original_whole_geometry(self):
        original,fast=self.waters()
        for margin in (0,10):
            fast.grids[margin]=CoastalGrid(build_grid(fast,spacing_m=250,margin_m=margin,chunk_cells=3))
            expected=[]
            for x in range(5):
                for y in range(5):
                    a=Vector(x*250,y*250)
                    for dx,dy in ((0,0),(1,0),(-1,0),(0,1),(0,-1),(1,1),(-1,1),(1,-1),(-1,-1)):
                        if not (0<=x+dx<5 and 0<=y+dy<5):continue
                        b=Vector((x+dx)*250,(y+dy)*250);expected.append((a,b,original.clear(a,b,margin)))
            with patch.object(fast.edge_index,'query',side_effect=AssertionError('Grid queries must use the exact stored predicates')):
                for a,b,value in expected:self.assertEqual(fast.clear(a,b,margin),value)
        # Both endpoints are wet, but the closed edge crosses a narrow island.
        self.assertTrue(fast.clear(Vector(0,0),Vector(0,0)))
        self.assertTrue(fast.clear(Vector(250,0),Vector(250,0)))
        self.assertFalse(fast.clear(Vector(0,0),Vector(250,0)))

    def test_closed_margin_and_off_grid_or_long_segments_keep_original_predicates(self):
        data=to_wkb(box(-10,-10,1010,1010));water=CoastalWater(data,'margin')
        grid=CoastalGrid(build_grid(water,margin_m=10));water.grids[10]=grid
        self.assertFalse(water.clear(Vector(0,250),Vector(0,250),10))
        self.assertTrue(water.clear(Vector(250,250),Vector(250,500),10))
        self.assertIsNone(grid.lookup((250.0000001,250),(250,500),10))
        self.assertIsNone(grid.lookup((0,0),(500,0),10))
        self.assertIsNone(grid.lookup((250,250),(250,500),11))
        self.assertIsNone(grid.lookup((-250,250),(0,250),10))

    def test_entire_water_connection_and_expansion_limits_are_identical(self):
        original,fast=self.waters();fast.grids[0]=CoastalGrid(build_grid(fast,margin_m=0))
        for a,b in ((Vector(0,0),Vector(250,0)),(Vector(30,20),Vector(600,200))):
            for limits in ({},{'max_expansions':1},{'max_cells':1}):
                with self.subTest(a=a,b=b,limits=limits):
                    self.assertEqual(original.connection(a,b,max_distance_m=1000,**limits),
                                     fast.connection(a,b,max_distance_m=1000,**limits))

    def test_persistent_cache_reuses_exact_flags_and_rejects_changed_identity(self):
        a,b=self.waters()
        with tempfile.TemporaryDirectory() as tmp:
            diagnostics={};cold=attach_grid(a,tmp,margin_m=0,diagnostics=diagnostics)
            self.assertEqual(diagnostics['geometry_cache']['0']['status'],'miss')
            with patch('infrastructure.coastal_grid.build_grid',side_effect=AssertionError('No repeated geometry build')):
                warm=attach_grid(b,tmp,margin_m=0,diagnostics=diagnostics)
            self.assertEqual(diagnostics['geometry_cache']['0']['status'],'hit')
            self.assertEqual(cold.flags.tobytes(),warm.flags.tobytes());self.assertFalse(warm.flags.flags.writeable)
            attach_grid(b,tmp,margin_m=10,diagnostics=diagnostics)
            self.assertEqual(diagnostics['geometry_cache']['10']['status'],'miss')
        with self.assertRaisesRegex(ValueError,'budget'):build_grid(a,max_cells=1)

    def test_batch_queries_match_scalar_including_zero_length_closed_margin_and_nonfinite(self):
        water,_=self.waters();start=Vector(0,0)
        ends=(start,Vector(250,0),Vector(0,250),Vector(1000,1000),Vector(-100,0))
        for margin in (0,10,100):
            self.assertEqual(water.clear_many(start,ends,margin),tuple(water.clear(start,p,margin) for p in ends))
        with self.assertRaises(ValueError):water.clear_many(start,(Vector(float('nan'),0),))
        with self.assertRaises(ValueError):water.clear_many(start,ends,-1)

    def test_batched_smoothing_retains_entire_original_search_and_multiple_candidates(self):
        water,_=self.waters();start,target=Vector(0,0),Vector(750,0);bounds=(-90,-90,1090,1090)
        for count in (1,3):
            args=dict(spacing_m=250,max_candidates=count,max_waypoints=128)
            scalar=generate_water_routes(start,target,bounds,water.clear,**args)
            batched=generate_water_routes(start,target,bounds,water.clear,clear_many=water.clear_many,**args)
            self.assertEqual(scalar,batched)
