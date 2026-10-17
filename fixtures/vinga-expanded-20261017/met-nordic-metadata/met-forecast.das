Attributes {
    x {
        String units "m";
        String standard_name "projection_x_coordinate";
    }
    y {
        String units "m";
        String standard_name "projection_y_coordinate";
    }
    projection_lcc {
        String grid_mapping_name "lambert_conformal_conic";
        String proj4 "+proj=lcc +lat_0=63 +lon_0=15 +lat_1=63 +lat_2=63 +no_defs +R=6.371e+06";
        Float64 standard_parallel 63.0, 63.0;
        Float64 longitude_of_central_meridian 15.0;
        Float64 latitude_of_projection_origin 63.0;
        Float64 earth_radius 6371000.0;
    }
    time {
        String units "seconds since 1970-01-01 00:00:00 +00:00";
        String standard_name "time";
        UInt32 _ChunkSizes 512;
    }
    forecast_reference_time {
        String units "seconds since 1970-01-01 00:00:00 +00:00";
        String standard_name "forecast_reference_time";
    }
    latitude {
        String grid_mapping "projection_lcc";
        String units "degree_north";
        String standard_name "latitude";
    }
    longitude {
        String grid_mapping "projection_lcc";
        String units "degree_east";
        String standard_name "longitude";
    }
    altitude {
        String grid_mapping "projection_lcc";
        String coordinates "longitude latitude";
        String standard_name "surface_altitude";
        String units "m";
    }
    land_area_fraction {
        String grid_mapping "projection_lcc";
        String coordinates "longitude latitude";
        String standard_name "land_area_fraction";
        String units "1";
    }
    air_temperature_2m {
        String grid_mapping "projection_lcc";
        String coordinates "longitude latitude";
        String units "K";
        String standard_name "air_temperature";
        UInt32 _ChunkSizes 1, 2321, 1796;
    }
    precipitation_amount {
        String coordinates "longitude latitude";
        String grid_mapping "projection_lcc";
        String units "kg/m^2";
        String standard_name "precipitation_amount";
        UInt32 _ChunkSizes 1, 2321, 1796;
    }
    wind_direction_10m {
        String coordinates "longitude latitude";
        String grid_mapping "projection_lcc";
        String units "degree";
        String standard_name "wind_from_direction";
        UInt32 _ChunkSizes 1, 2321, 1796;
    }
    wind_speed_10m {
        String coordinates "longitude latitude";
        String grid_mapping "projection_lcc";
        String units "m/s";
        String standard_name "wind_speed";
        UInt32 _ChunkSizes 1, 2321, 1796;
    }
    wind_speed_of_gust {
        String coordinates "longitude latitude";
        String grid_mapping "projection_lcc";
        String units "m/s";
        String standard_name "wind_speed_of_gust";
        UInt32 _ChunkSizes 1, 2321, 1796;
    }
    cloud_area_fraction {
        String grid_mapping "projection_lcc";
        String coordinates "longitude latitude";
        String units "1";
        String standard_name "cloud_area_fraction";
        UInt32 _ChunkSizes 1, 2321, 1796;
    }
    air_pressure_at_sea_level {
        String grid_mapping "projection_lcc";
        String coordinates "longitude latitude";
        String units "Pa";
        String standard_name "air_pressure_at_sea_level";
        UInt32 _ChunkSizes 1, 2321, 1796;
    }
    integral_of_surface_downwelling_longwave_flux_in_air_wrt_time {
        String grid_mapping "projection_lcc";
        String coordinates "longitude latitude";
        String units "J/m^2";
        String standard_name "integral_of_surface_downwelling_longwave_flux_in_air_wrt_time";
        UInt32 _ChunkSizes 1, 2321, 1796;
    }
    integral_of_surface_downwelling_shortwave_flux_in_air_wrt_time {
        String grid_mapping "projection_lcc";
        String coordinates "longitude latitude";
        String units "W s/m^2";
        String standard_name "integral_of_surface_downwelling_shortwave_flux_in_air_wrt_time";
        UInt32 _ChunkSizes 1, 2321, 1796;
    }
    relative_humidity_2m {
        String grid_mapping "projection_lcc";
        String coordinates "longitude latitude";
        String units "1";
        String standard_name "relative_humidity";
        UInt32 _ChunkSizes 1, 2321, 1796;
    }
    probability_of_snow_phase {
        String grid_mapping "projection_lcc";
        String coordinates "longitude latitude";
        String units "1";
        String standard_name "snowfall_amount";
        UInt32 _ChunkSizes 1, 2321, 1796;
    }
    probability_of_thunder {
        String grid_mapping "projection_lcc";
        String coordinates "longitude latitude";
        String units "1";
        String standard_name "thunderstorm_probability";
        UInt32 _ChunkSizes 1, 2321, 1796;
    }
    NC_GLOBAL {
        String Conventions "CF-1.0";
        String institution "Norwegian Meteorological Institute, met.no";
        String creator_url "met.no";
        String geospatial_lat_min "51.0";
        String geospatial_lat_max "88.0";
        String geospatial_lon_min "-20.0";
        String geospatial_lon_max "80.0";
        String references "unknown";
        String source "meps";
        String summary "Based on model data from MEPS (MetCoOp-Ensemble Prediction System) and observations";
        String meps_forecast_reference_time "1792184400";
        String history "Created 2026-10-17T00:26:37Z";
        String license "https://www.met.no/en/free-meteorological-data/Licensing-and-crediting";
    }
    DODS_EXTRA {
        String Unlimited_Dimension "time";
    }
}
