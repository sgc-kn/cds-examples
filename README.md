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

The notebooks require a few Python dependencies. We list them in
[`pyproject.toml`](pyproject.toml). We develop and test the notebooks
on Python 3.12 with the specific package versions listed in
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

Alternatively, if you have Make installed, run `make notebook` to
execute the above commands in one go.

----

### Examples

Each notebook provides usage examples for one CDS dataset.

**Lake Surface Water Temperature:**
[CDS dataset](https://cds.climate.copernicus.eu/cdsapp#!/dataset/satellite-lake-water-temperature)
[Notebook](./lake-surface-water-temperature.ipynb)
