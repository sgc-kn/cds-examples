import cdsapi
import json
import netCDF4
import os
import pandas
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

#
# Configuration
#

data_path = "data/sis-ecde-climate-indicators"
cds_api_key = None

areas = dict(
        konstanz = "-sellonlatbox,9,9.5,47,47.5"
        )

#
# Password/Key Management
#
# can be ignored if secrets are configured above
#

def get_pass(path):
    proc = subprocess.run(
            ['pass', path], capture_output=True, text=True, check=True
            )
    return proc.stdout.splitlines()[0]

def get_cds_api_key():
    global cds_api_key
    if cds_api_key is not None:
        return cds_api_key
    else:
        path = "work/stadtkn/cds-beta.climate.copernicus.eu/api-key"
        cds_api_key = get_pass(path)
        return cds_api_key

#
# Download data from CDS, if not already available locally
#

def load_reanalysis():
    dataset = "sis-ecde-climate-indicators"
    request = {
            'variable': [
                'growing_degree_days', 'heating_degree_days',
                'cooling_degree_days', 'tropical_nights', 'hot_days',
                'warmest_three_day_period', 'heatwave_days', 'high_utci_days',
                'frost_days', 'total_precipitation',
                'maximum_consecutive_five_day_precipitation',
                'extreme_precipitation_total',
                'frequency_of_extreme_precipitation', 'consecutive_dry_days',
                'duration_of_meteorological_droughts',
                'magnitude_of_meteorological_droughts',
                'days_with_high_fire_danger', 'extreme_wind_speed_days',
                'fire_weather_index'
                ],
            'origin': 'reanalysis',
            'temporal_aggregation': ['yearly'],
            'spatial_aggregation': 'gridded',
            'other_parameters': ['30_c', '35_c', '40_c']
            }
    path = data_path + "/cds/reanalysis.zip"
    if os.path.exists(path):
        print(f"reanalysis dataset locally available")
    else:
        print(f"download reanalysis dataset")
        client = cdsapi.Client(url=api_url, key=api_key)
        os.makedirs(data_path + '/cds', exist_ok = True)
        client.retrieve(dataset, request, path)

    return path

def load_projections():
    dataset = "sis-ecde-climate-indicators"
    request = {
        'variable': [
            'growing_degree_days', 'heating_degree_days',
            'cooling_degree_days', 'tropical_nights', 'hot_days',
            'warmest_three_day_period', 'heatwave_days', 'frost_days',
            'total_precipitation',
            'maximum_consecutive_five_day_precipitation',
            'extreme_precipitation_total',
            'frequency_of_extreme_precipitation', 'consecutive_dry_days',
            'duration_of_meteorological_droughts',
            'magnitude_of_meteorological_droughts',
            'days_with_high_fire_danger', 'extreme_wind_speed_days',
            'fire_weather_index'
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
    path = data_path + "/cds/projections.zip"
    if os.path.exists(path):
        print(f"projections dataset locally available")
    else:
        print(f"download projections dataset")
        client = cdsapi.Client(url=api_url, key=api_key)
        os.makedirs(data_path + '/cds', exist_ok = True)
        client.retrieve(dataset, request, path)

    return path

#
# Extract netCDF files from CDS zip files
#

def clean_nc_directory():
    if os.path.exists(data_path + '/nc'):
        shutil.rmtree(data_path + '/nc')

def unzip_dataset(path):
    os.makedirs(data_path + '/nc', exist_ok=True)
    with zipfile.ZipFile(path, 'r') as f:
        f.extractall(data_path + '/nc')
        files = f.namelist()
    paths = list(map(lambda n: data_path + '/nc/' + n, files))
    return paths

def load_nc_files():
    nc_path = data_path + '/nc'
    if os.path.exists(nc_path):
        files = os.listdir(nc_path)
        return [ nc_path + '/' + f for f in files if f.endswith('.nc') ]
    else:
        reanalysis = load_reanalysis()
        projections = load_projections()
        r_nc = unzip_dataset(reanalysis)
        p_nc = unzip_dataset(projections)
        return r_nc + p_nc

#
# Extract timeseries data from netCDF
#

def clean_csv_directory():
    if os.path.exists(data_path + '/csv'):
        shutil.rmtree(data_path + '/csv')

def per_nc(nc_file):
    proc = subprocess.run(['cdo', 'showvar', nc_file],
                          capture_output=True, text=True, check=True
                          )
    vars = proc.stdout.split()
    for var in vars:
        per_nc_var(nc_file, var)

def per_nc_var(nc_file, var):
    for area in areas.keys():
        per_nc_var_area(nc_file, var, area)

def per_nc_var_area(nc_file, var, area):
    print(nc_file + ":" + var)

    # extract data
    meta = meta_of_nc_var(nc_file, var)
    ts = ts_of_nc_var_area(nc_file, var, area)

    # extend metadata
    meta['area'] = area
    meta['area-cdo-op'] = areas[area]

    # write timeseries to csv
    os.makedirs(data_path + '/csv', exist_ok=True)
    nc_name = os.path.basename(nc_file).removesuffix('.nc')
    csv_path = f"{data_path}/csv/{nc_name}-{var}-{area}.csv"
    ts.to_csv(csv_path, sep=',')

    # write metadata to json
    json_path = f"{data_path}/csv/{nc_name}-{var}-{area}.json"
    with open(json_path, 'w') as f:
        json.dump(meta, f)

    return ts, meta

def meta_of_nc_var(nc_file, var):
    ds = netCDF4.Dataset(nc_file)
    meta = dict()
    for attr in ds.variables[var].ncattrs():
        if not attr.startswith('_'):
            meta[attr] = ds.variables[var].getncattr(attr)
    return meta

def ts_of_nc_var_area(nc_vile, var, area):
    operators = ['-outputtab,date,value,nohead', '-fldmean', areas[area]]

    gridf = fixed_grid(nc_file)
    if gridf is not None:
        operators.append('-setgrid,' + gridf.name)

    csvf = tempfile.NamedTemporaryFile('wt',
                                        prefix=sys.argv[0] + '.tmp-'
                                        , suffix='.csv'
                                        , delete_on_close=False)

    proc = subprocess.run(['cdo'] + operators + [nc_file],
                          text=True, stdout=csvf, check=True)

    df = pandas.read_csv(csvf.name, names=['date', 'value'], sep=r'\s+')
    return df

def fixed_grid(nc_file):
    gridf = tempfile.NamedTemporaryFile('wt',
                                        prefix=sys.argv[0] + '.tmp-'
                                        , suffix='.grid'
                                        , delete_on_close=False)

    proc = subprocess.run(['cdo', 'griddes', nc_file],
                          capture_output=True, text=True, check=True)

    old_grid = proc.stdout
    if re.search('gridtype *= generic', old_grid):
        # run short sanity checks
        assert re.search('xname *= lon', old_grid), 'x-axis mismatch'
        assert re.search('yname *= lat', old_grid), 'y-axis mismatch'

        # patch grid description and write to file
        gridf = tempfile.NamedTemporaryFile(
                'wt',
                prefix=sys.argv[0] + '.tmp-',
                suffix='.grid',
                delete_on_close=False)
        new_grid = re.sub('gridtype *= generic', 'gridtype  = lonlat', old_grid)
        print(new_grid, file=gridf, end='')
        print('xlongname = "longitude"', file=gridf)
        print('xunits    = "degrees_east"', file=gridf)
        print('ylongname = "latitude"', file=gridf)
        print('yunits    = "degrees_north"', file=gridf)
        gridf.close()

        return gridf
    else:
        return None

def zip_csv_directory():
    zipf = os.path.basename(sys.argv[0]).removesuffix('.py')
    shutil.make_archive(zipf, 'zip', data_path + '/csv')

#
# Define what to do if this is executed as a script
#

if __name__ == "__main__":
    clean_csv_directory()
    nc_files = load_nc_files()
    for nc_file in sorted(nc_files):
        per_nc(nc_file)
    zip_csv_directory()
