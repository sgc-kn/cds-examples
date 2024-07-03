notebook: setup
	venv/bin/jupyter-notebook

setup: venv
venv: requirements.txt
	# setup bare venv
	python -m venv venv
	venv/bin/pip install --upgrade pip
	# pinned dependencies
	venv/bin/pip install -r requirements.txt
	touch venv

setup: ~/.cdsapirc
~/.cdsapirc:
	@echo Please set your CDS API key in the ~/.cdsapirc text file.
	@echo It should look like this:
	@echo 'url: https://cds.climate.copernicus.eu/api/v2'
	@echo 'key: <UID>:<API key>'
	@false

upgrade-dependencies: venv
	venv/bin/pip install --upgrade pip pip-tools
	# derive requirements.txt from pyproject.toml
	# (we pin and track all versions in requirements.txt)
	venv/bin/pip-compile --upgrade --strip-extras --quiet
	# install the updated versions in the virtual environment
	venv/bin/pip install -r requirements.txt
	touch venv

clean:
	rm -rf venv
