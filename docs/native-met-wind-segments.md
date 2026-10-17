# Frozen MET wind on Vinga route segments

`infrastructure/met_wind_segments.py` samples the already hash-frozen MET Nordic
wind subset on a segment in the Vinga WGS84-AEQD route frame. It transforms
coordinates to the product's declared spherical LCC grid, converts the official
`wind_from_direction` values (0° north, 90° east) to true east/north components,
interpolates those components bilinearly in native space and linearly in time,
then maps the vector differential into the route frame. No angle interpolation,
grid-axis-as-east/north assumption, network fetch, or extrapolation is used.
MET's [Nordic product documentation](https://github.com/metno/NWPdocs/wiki/MET-Nordic-dataset)
declares spherical Lambert conformal conic, wind speed/direction at 10 m, a
10-minute average, and direction-from with 0° north/90° east. The CF/NERC
[`wind_from_direction`](https://vocab.nerc.ac.uk/standard_name/wind_from_direction/)
definition identifies a horizontal air-velocity vector and links the standard
name to `earthrelativewinddirection`; the direction is therefore normalized as
a geographic bearing before interpolation. MET's older grid-axis rotation
example applies to separate model-grid x/y components and is not used for this
direction field.

The whole affine route segment is enclosed by a disk centered at the AEQD origin.
WGS84 ellipsoid metric bounds enclose that disk in a latitude/longitude box;
the existing rational interval LCC enclosure then identifies every touched
native cell. An extra 1 m support margin covers the observed 0.2491 m maximum
alignment difference across the 56 saved provider-coordinate nodes. This is a
regional fixture consistency check, not a global datum-accuracy claim.

For the declared trilinear vector-component interpolation, the wind magnitude
over a cell cannot exceed the greatest corner magnitude. A point on the segment
above the configured test limit proves an exceedance. If the conservative bound
crosses the limit and no on-segment point demonstrates an exceedance, the result
is `insufficient_evidence`; sparse samples never certify passage. The result
`within_interpolation_model` is limited to the consumer interpolation model.

Run the frozen Vinga case offline:

```bash
python -B -m scripts.native_met_wind_segment --output artifacts/native-met-wind-segment/report.json
python -B -m unittest tests.test_met_wind_segments -v
```

At the fixture's 10 m/s test cap the real frozen wind produces an observed
exceedance. At 18 m/s its native interpolation bound is within the test limit.
Neither result is an operational threshold or approved route: `issued_at` and
wind validity-mask semantics are still unknown, averaging-window placement is
unverified, and the native wind run is not proven compatible with the marine
forecast runs. Those gates remain separate in regional planning. The sample's
actual values are not used with the existing synthetic polar because they exceed
that polar's validated test-data range. Current, waves and boat performance are
not used by this diagnostic. Depth, land completeness and navigational safety
remain unknown/not assessed.
