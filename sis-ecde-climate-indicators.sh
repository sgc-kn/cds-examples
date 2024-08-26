#!/usr/bin/env bash

set -Eeuo pipefail

cds_path=data/sis-ecde-climate-indicators/cds
nc_path=data/sis-ecde-climate-indicators/nc
csv_path=data/sis-ecde-climate-indicators/csv
area=9,9.5,47,47.5 # bounding box: minlon,maxlon,minlat,maxlat

#
# Download data from CDS, if not already available locally
#

load_api_key () {
  CDS_BETA_API_KEY=$(pass work/stadtkn/cds-beta.climate.copernicus.eu/api-key)
  export CDS_BETA_API_KEY
}

reanalysis="$cds_path/reanalysis.zip"
if [ ! -f "$reanalysis" ] ; then
  echo download reanalysis from cdsapi ...
  mkdir -p "$(dirname "$reanalysis")"

  if [ -z "${CDS_BETA_API_KEY-}" ] ; then
    load_api_key
  fi

  if [ -d "./venv" ] ; then
    python=./venv/bin/python
  else
    python=python3
  fi

  $python << EOF
import cdsapi, os

api_key = "$CDS_BETA_API_KEY"

api_url = "https://cds-beta.climate.copernicus.eu/api"

dataset = "sis-ecde-climate-indicators"
request = {
    'variable': [
        'growing_degree_days', 'heating_degree_days', 'cooling_degree_days',
        'tropical_nights', 'hot_days', 'warmest_three_day_period',
        'heatwave_days', 'high_utci_days', 'frost_days', 'total_precipitation',
        'maximum_consecutive_five_day_precipitation',
        'extreme_precipitation_total', 'frequency_of_extreme_precipitation',
        'consecutive_dry_days', 'duration_of_meteorological_droughts',
        'magnitude_of_meteorological_droughts', 'days_with_high_fire_danger',
        'extreme_wind_speed_days', 'fire_weather_index'
      ],
    'origin': 'reanalysis',
    'temporal_aggregation': ['yearly'],
    'spatial_aggregation': 'gridded',
    'other_parameters': ['30_c', '35_c', '40_c']
}
client = cdsapi.Client(url=api_url, key=api_key)
client.retrieve(dataset, request, "$reanalysis")
EOF
fi

projections="$cds_path/projections.zip"
if [ ! -f "$projections" ] ; then
  echo download projections from cdsapi ...

  mkdir -p "$(dirname "$projections")"

  if [ -z "$CDS_BETA_API_KEY" ] ; then
    load_api_key
  fi

  if [ -d "./venv" ] ; then
    python=./venv/bin/python
  else
    python=python3
  fi

  python << EOF
import cdsapi, os

api_key = "$CDS_BETA_API_KEY
api_url = "https://cds-beta.climate.copernicus.eu/api"

dataset = "sis-ecde-climate-indicators"
request = {
    'variable': [
        'growing_degree_days', 'heating_degree_days', 'cooling_degree_days',
        'tropical_nights', 'hot_days', 'warmest_three_day_period',
        'heatwave_days', 'frost_days', 'total_precipitation',
        'maximum_consecutive_five_day_precipitation',
        'extreme_precipitation_total', 'frequency_of_extreme_precipitation',
        'consecutive_dry_days', 'duration_of_meteorological_droughts',
        'magnitude_of_meteorological_droughts', 'days_with_high_fire_danger',
        'extreme_wind_speed_days', 'fire_weather_index'
      ],
    'origin': 'projections',
    'gcm': ['mpi_esm_lr'],
    'rcm': ['cclm4_8_17'],
    'experiment': ['rcp4_5', 'rcp8_5'],
    'ensemble_member': ['r1i1p1'],
    'temporal_aggregation': ['yearly'],
    'spatial_aggregation': 'gridded',
    'other_parameters': ['30_c', '35_c', '40_c']
}

client = cdsapi.Client(url=api_url, key=api_key)
client.retrieve(dataset, request, "$projections")
EOF
fi

#
# Clean and recreate target directories
#

rm -rf $nc_path
mkdir -p $nc_path
rm -rf $csv_path
mkdir -p $csv_path

#
# Unzip CDS zip files
#

for f in "$cds_path"/*.zip ; do
  unzip "$f" -d "$nc_path"
done

#
# Per variable in netCDF file, do the following
#

per_nc_var () {
  nc=$1
  var=$2

  #
  # Set output filenames
  #
  csv="$csv_path/$(basename "${nc%.nc}")-$var".csv
  meta="$csv_path/$(basename "${nc%.nc}")-$var".meta.csv

  #
  # Avoid file overwrite
  #
  test ! -e "$csv" || (echo ERROR: "$csv" exists already >&2 && false)

  #
  # Some netCDF files have broken grid descriptions
  # The following code handles these cases
  #
  if cdo griddes "$nc" | grep 'gridtype *= generic' > /dev/null ; then
    # create temporary file with grid description
    gridf=$(mktemp tmp.grid.XXXXXXXXXX)
    cdo griddes "$nc" > "$gridf"

    # fix gridtype
    sed 's/gridtype *= generic/gridtype = lonlat/' -i "$gridf"

    # check and fix x-axis
    grep 'xname *= lon' "$gridf" > /dev/null # check
    echo 'xlongname = "longitude"' >> "$gridf" # fix
    echo 'xunits = "degrees_east"' >> "$gridf" # fix

    # check and fix y-axis
    grep 'yname *= lat' "$gridf" > /dev/null # check
    echo 'ylongname = "latitude"' >> "$gridf" # fix
    echo 'yunits = "degrees_north"' >> "$gridf" # fix

    # configure cdo operator
    fix_grid=("-setgrid,$gridf")

    # prepare cleanup
    clean_grid () {
      rm "$gridf"
    }
  else
    fix_grid=()
    clean_grid () {
      true
    }
  fi

  #
  # Produce CSV
  #

  echo "date,value" > "$csv"
  cdo -L \
    -outputtab,date,value,nohead \
    -setname,"$(basename "${nc%.nc}")" \
    -fldmean \
    -sellonlatbox,$area \
    "${fix_grid[@]}" \
    "$nc" | column -to, >> "$csv"

  # cleanup temporary grid description
  clean_grid

  #
  # Write metadata
  #

  echo "key,value" > "$meta"
  echo "area,\"$area\"" >> "$meta"
  cdo "showattribute,$var@" "$nc" \
    | tail -n +2 \
    | sed 's/^\s*\([a-zA-Z0-9_]*\)\s*=\s*"*\([^"]*\)"*$/\1,"\2"/' \
    >> "$meta"
}

#
# Per netCDF file, do the following
#

per_nc () {
  nc=$1

  # read the variable names defined in netCDF and iterate
  cdo showvar "$nc" | tr ' ' '\n' | xargs -l | while read -r var ; do
    per_nc_var "$nc" "$var"
  done
}

#
# run loop for all netCDF files
#

for nc in "$nc_path"/*.nc ; do
  per_nc "$nc"
done
