# Copernicus Climate Data Store Examples

We here provide examples for loading and preprocessing data from the
[Copernicus Climate Data Store (CDS)][cds] for application in city
governments. All examples are tailored for the city of Constance. The
work is part of the [CoKLIMAx][coklimax] project and the [Smart Green
City Konstanz][sgc] program.

[cds]: https://cds.climate.copernicus.eu/
[coklimax]: https://www.iigs.uni-stuttgart.de/forschung/coklimax/
[sgc]: https://smart-green-city-konstanz.de/

---

The notebooks and scripts require a few Python dependencies. We list
them in [`pyproject.toml`](pyproject.toml). We develop and test  on
Python 3.12 with the specific package versions listed in
[`requirements.txt`](requirements.txt).

We recommend installing the dependencies into a virtual environment.
E.g. on a typical Linux setup you can do the following in the project
root directory.

```shell
python -m venv venv
venv/bin/pip install --upgrade pip
venv/bin/pip install -r requirements.txt
venv/bin/jupyter-notebook
```

----

### Examples

Each notebook/script provides usage examples for one CDS dataset.

**Heat Wave Days:**
- [CDS dataset](https://cds.climate.copernicus.eu/cdsapp#!/dataset/sis-heat-and-cold-spells)
- [Notebook](./sis-heat-and-cold-spells.ipynb)
- [CSV Output (Germany)](./sis-heat-and-cold-spells.csv.zip)

**Satellite Lake Water Temperature:**
- [CDS dataset](https://cds.climate.copernicus.eu/cdsapp#!/dataset/satellite-lake-water-temperature)
- [Notebook](./satellite-lake-water-temperature.ipynb)
- [CSV Output (Bodensee)](./satellite-lake-water-temperature.csv)

**Climate indicators for Europe from 1940 to 2100:**
- [CDS dataset](https://cds-beta.climate.copernicus.eu/datasets/sis-ecde-climate-indicators)
- [Script](./sis-ecde-climate-indicators.py)
- [Additional system dependency: CDO](https://code.mpimet.mpg.de/projects/cdo/wiki)
- [CSV Output](./sis-ecde-climate-indicators.zip)

---

### License

We distribute our work under the MIT license. We provide the full
license terms in the [`LICENSE`](./LICENSE) file.
