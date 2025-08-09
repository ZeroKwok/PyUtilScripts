.PHONY: build upload test clean

build: clean
	@echo "Building..."
	python -m build

upload:
	@echo "Uploading..."
	twine upload --repository testpypi dist/*
	twine upload dist/*

test: clean
	@echo "Testing..."
	python -m pip install -e .[dev]

clean:
	rm -fr dist/*