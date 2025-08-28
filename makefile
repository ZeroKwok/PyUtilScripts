.PHONY: build upload test clean

build: clean
	@echo "Building..."
	python -m build

upload:
	@echo "Uploading..."
	twine upload --repository testpypi dist/*
	twine upload dist/*

setup:
	@echo "Setting up..."
	python -m pip install .

test: clean
	@echo "Testing..."
	python -m pip install -e .[dev]
	pytest tests

clean:
	rm -fr dist/*