ENVS := flake8,py27,py36
export PYTHONPATH := $(CURDIR)/lib:$(CURDIR)/test
addon_xml := addon.xml

# Collect information to build as sensible package name
name = $(shell xmllint --xpath 'string(/addon/@id)' $(addon_xml))
version = $(shell xmllint --xpath 'string(/addon/@version)' $(addon_xml))
git_branch = $(shell git rev-parse --abbrev-ref HEAD)
git_hash = $(shell git rev-parse --short HEAD)

zip_name = $(name)-$(version)-$(git_branch)-$(git_hash).zip
include_files = addon.py addon.xml changelog.txt LICENSE.txt README.md lib/ resources/
include_paths = $(patsubst %,$(name)/%,$(include_files))
exclude_files = \*.new \*.orig \*.pyc \*.pyo
zip_dir = $(name)/

blue = \e[1;34m
white = \e[1;37m
reset = \e[0m

.PHONY: test

all: test zip

package: zip

test: sanity unit

sanity: tox pylint

tox:
	@echo -e "$(white)=$(blue) Starting sanity tox test$(reset)"
	tox -q -e $(ENVS)

pylint:
	@echo -e "$(white)=$(blue) Starting sanity pylint test$(reset)"
	pylint lib/ test/

addon: clean
	@echo -e "$(white)=$(blue) Starting sanity addon tests$(reset)"
	kodi-addon-checker . --branch=krypton
	kodi-addon-checker . --branch=leia

unit: clean
	@echo -e "$(white)=$(blue) Starting unit tests$(reset)"
	python -m unittest discover
#	coverage run -m unittest discover

zip: clean
	@echo -e "$(white)=$(blue) Building new package$(reset)"
	@rm -f ../$(zip_name)
	cd ..; zip -r $(zip_name) $(include_paths) -x $(exclude_files)
	@echo -e "$(white)=$(blue) Successfully wrote package as: $(white)../$(zip_name)$(reset)"

clean:
	@echo -e "$(white)=$(blue) Cleaning up$(reset)"
	find resources/ test/ -name '*.pyc' -type f -delete
	find resources/ test/ -name '__pycache__' -type d -delete
	rm -rf .pytest_cache/ .tox/ *.log
