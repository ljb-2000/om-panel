.PHONY: docs

init:
	pip install -r requirements.txt

run:
	PYTHONPATH=. ./bin/om_panel

clean:
	rm -rf dist/

test:
	echo "TBD"

publish:
	python setup.py register
	python setup.py sdist upload
	python setup.py bdist_wheel upload
