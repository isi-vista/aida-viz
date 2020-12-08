<!-- CI configuration disabled due to changes in Travis subscription model. Reactivate when issue has been resolved. -->
<!-- [![Build status](https://travis-ci.com/isi-vista/aida-viz.svg?branch=master)](https://travis-ci.com/isi-vista/aida-viz?branch=master) -->

# AIDA Vizualization Tools

This repository contains the package `aida_viz`, a tool for visualizing AIF knowledge elements in a simple HTML format.

## Installation

We recommend setting up a virtual environment for managing dependencies by using tools such as [`conda`](https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html) or [`virtualenv`](https://virtualenv.pypa.io/en/latest/).

Install `aida_viz` by downloading this repository and running `pip install $AIDA_VIZ_REPO`, where `$AIDA_VIZ_REPO` is the top-level directory of this repository.

You will also need to manually install the Python package included in the [AIDA Interchange Format repository](https://github.com/NextCenturyCorporation/AIDA-Interchange-Format) (you do not need the Java installation).

## Usage

To generate visualizations, `aida_viz` requires an SQLite database file containing the text documents found in the relevant AIDA Evaluation Source Data (for example, the Phase 1 Evaluation Source Data `LDC2019E42` is available via the [LDC Catalog](https://catalog.ldc.upenn.edu)).

**The easiest way to obtain this SQLite database file is to contact the maintainers of this repository and request it from them.** However, it is possible to generate the database from the original LDC source data.

### Generating the Database

**Skip this section** if you have obtained the SQLite database file from this repository's maintainers.

Generating the database from the LDC-provided `.tgz` file is a two-step process: 

1. Convert the source data in `.tgz` format to `.zip` format. Use the script [tar_gz_to_zip.py](https://github.com/isi-vista/vistautils/blob/master/vistautils/scripts/tar_gz_to_zip.py) found in the [isi-vista/vistautils](https://github.com/isi-vista/vistautils) repository.

2. Use the resulting `.zip` file to populate the database using the following command:

	```
	python -m aida_viz.corpus -z $AIDA_SOURCE_ZIP -d $AIDA_SOURCE_SQLITE
	```

Where: 
- `$AIDA_SOURCE_ZIP` is the location of the converted `.zip` version of the source data.
- `$AIDA_SOURCE_SQLITE` is the name of the new file where the database will be written (this file should be given the `.sqlite` extension).

### Generating Visualizations

Now that you have the SQLite database file `$AIDA_SOURCE_SQLITE`, generate a visualization of an AIF `.ttl` file with the following command:

```
python -m aida_viz -a $AIDA_AIF_TTL -d $AIDA_CORPUS_SQLITE -o $RESULTS
```

Where:
- `$AIDA_AIF_TTL` is the location of the AIF `.ttl` file that you would like to visualize.
- `$RESULTS` is the **new** directory location where the results should be written.

# Docker

```
$ echo set variables on host
$ export INPUT=path-to-file.ttl
$ export SQLITE=path-to-file.sqlite
$ export RESULTS=path-to-directory
$ echo build docker image
$ docker build . -t aida-viz
$ echo run aida_viz module in a docker container
$ docker run -it -v $INPUT:$INPUT -v $RESULTS:$RESULTS -v $SQLITE:$SQLITE -e AIDA_AIF_TTL=$INPUT -e AIDA_CORPUS_SQLITE=$SQLITE -e RESULTS=$RESULTS --name viz-test aida-viz:latest /bin/bash -c "python -m aida_viz -a ${INPUT} -d ${SQLITE} -o ${RESULTS}"
```
Run sequentially over a list of `*.ttl` files using the `run-batch.sh` script.
```
$ echo list all `*.ttl` files in a text file; find $(pwd) -file '*.ttl' &>> ttl-list-file.txt
$ export TTL_LIST_FILE=path-to-ttl-list-file.txt
$ ./run-batch.sh ${TTL_LIST_FILE} $SQLITE $RESULTS
```

# Contributing

Install the development requirements by running `pip install dev-requirements.txt`.

Run `make precommit` before committing.

WARNING: contributor infrastructure is still under development. Please contact the repository maintainers if you would like to contribute.
