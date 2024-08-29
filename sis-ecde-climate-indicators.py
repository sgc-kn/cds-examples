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
        berlin = dict(lat = 52.518611, lon = 13.408333),
        hamburg = dict(lat = 53.550556, lon = 9.993333),
        konstanz = dict(lat = 47.66336, lon = 9.17598),
        madrid = dict(lat = 40.4125, lon = -3.703889),
        mailand = dict(lat = 45.4625, lon = 9.186389),
        paris = dict(lat = 48.856667, lon = 2.351667),
        )
# EPSG:4326 CRS (WGS84 with decimal degree); data from Wikipedia

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
    print(nc_file + ":" + var)

    # extract metadata
    meta = meta_of_nc_var(nc_file, var)

    # extend metadata
    meta['areas'] = areas.copy()
    meta['areas']['_crs'] = "EPSG:4326"

    # prepare folder and file name
    os.makedirs(data_path + '/csv', exist_ok=True)
    nc_name = os.path.basename(nc_file).removesuffix('.nc')

    # write metadata to json
    json_path = f"{data_path}/csv/{nc_name}-{var}.json"
    with open(json_path, 'w') as f:
        json.dump(meta, f)

    # collect timeseries for all areas
    tss = []
    for area, point in areas.items():
        ts = ts_of_nc_var_point(nc_file, var, point)
        ts = ts.rename(columns = {'value': area})
        tss.append(ts)

    # merge timeseries into single dataframe
    df = pandas.concat(tss, axis=1)

    # write dataframe to csv
    csv_path = f"{data_path}/csv/{nc_name}-{var}.csv"
    df.to_csv(csv_path, sep=',')


def meta_of_nc_var(nc_file, var):
    ds = netCDF4.Dataset(nc_file)
    meta = dict()
    for attr in ds.variables[var].ncattrs():
        if not attr.startswith('_'):
            meta[attr] = ds.variables[var].getncattr(attr)
    return meta

def ts_of_nc_var_point(nc_vile, var, point):
    nnf= nearest_neighbor(point) # file with nearest neighbour grid

    area_op = '-remapnn,' + nnf.name

    operators = ['-outputtab,date,value,nohead', area_op]

    # fix broken CDS grid description, when applicable
    gridf = fixed_grid(nc_file)
    if gridf is not None:
        operators.append('-setgrid,' + gridf.name)

    #
    # Apply CDO operators
    #

    # cdo clutters the stdout of outputtab with info of the remap operator
    # we circumvent this by applying the outputtab operator separately

    # fist apply all operators but outputtab
    ncf = tempfile.NamedTemporaryFile('wt',
                                     prefix=sys.argv[0] + '.tmp-'
                                     , suffix='.nc'
                                     , delete_on_close=False)
    ncf.close()
    cmd = ['cdo'] + operators[1:] + [nc_file, ncf.name]
    subprocess.run(cmd, text=True, check=True)

    # then apply outputtab separately
    csvf = tempfile.NamedTemporaryFile('wt',
                                        prefix=sys.argv[0] + '.tmp-'
                                        , suffix='.csv'
                                        , delete_on_close=False)

    cmd = ['cdo'] + operators[:1] + [ncf.name]
    proc = subprocess.run(cmd, text=True, stdout=csvf, check=True)

    #
    # Parse the csv into a pandas dataframe
    #

    df = pandas.read_csv(csvf.name, names=['date', 'value'], sep=r'\s+')
    df = df.set_index('date')
    return df

def nearest_neighbor(point):
    gridf = tempfile.NamedTemporaryFile('wt',
                                        prefix=sys.argv[0] + '.tmp-'
                                        , suffix='.grid'
                                        , delete_on_close=False)

    lines = [
            "gridtype = lonlat",
            "xsize = 1",
            "ysize = 1",
            f"xfirst = {point['lon']}",
            f"yfirst = {point['lat']}",
            ]

    print(*lines, sep='\n', file=gridf)
    gridf.close()

    return gridf

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
