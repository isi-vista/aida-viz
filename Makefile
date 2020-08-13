default:
	@echo "an explicit target is required"

SOURCE_DIR_NAME=aida_viz

PYTEST:=pytest --suppress-no-test-exit-code

MYPY:=mypy $(MYPY_ARGS) $(SOURCE_DIR_NAME)

lint:
	pylint $(SOURCE_DIR_NAME)

mypy:
	$(MYPY)

black-fix:
	isort -rc .
	black $(SOURCE_DIR_NAME)

black-check:
	black --check $(SOURCE_DIR_NAME)

check: black-check mypy lint

precommit: black-fix check
