notebook: setup
	venv/bin/jupyter-notebook

setup: venv
venv: requirements.txt
	# setup bare venv
	python -m venv venv
	venv/bin/pip install --upgrade pip
	# pinned dependencies
	venv/bin/pip install -r requirements.txt
	# development tools
	venv/bin/pip install pip-tools notebook
	touch venv

setup: ~/.cdsapirc
~/.cdsapirc:
	@echo Please set your CDS API key in the ~/.cdsapirc text file.
	@echo It should look like this:
	@echo 'url: https://cds.climate.copernicus.eu/api/v2'
	@echo 'key: <UID>:<API key>'
	@false

.PHONY: update
update: venv
	# derive requirements.txt from pyproject.toml
	# (we pin and track all versions in requirements.txt)
	venv/bin/pip-compile --strip-extras --quiet
	# install the updated version in the virtual environment
	venv/bin/pip install -r requirements.txt
	touch venv

setup: data/esa-cci-lakes.csv
data/esa-cci-lakes.csv:
	mkdir -p data
	wget https://zenodo.org/records/6699376/files/ESA_CCI_static_lake_mask_v2_1km_UoR_metadata_fv2.1_06Oct2021.csv?download=1 -O $@

.PHONY: clean
clean:
	rm -rf venv esa-cci-lakes.csv
