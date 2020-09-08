#!/usr/bin/env python

import setuptools

setuptools.setup(
    name="aida_viz",
    version="0.1.0",
    author="USC Information Sciences Institute",
    packages=["aida_viz"],
    python_requires=">=3.8",
    install_requires=[
        "attrs==19.2.0",
        "vistautils==0.19.0",
        "immutablecollections==0.9.0",
        "rdflib",
        "nltk",
        "jinja2",
        "pandas",
        "tqdm",
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
