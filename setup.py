#!/usr/bin/python

import setuptools

with open("./pdns_protobuf_receiver/__init__.py", "r") as fh:
    for line in fh.read().splitlines():
        if line.startswith('__version__'):
            VERSION = line.split('"')[1]
      
with open("README.md", "r") as fh:
    LONG_DESCRIPTION = fh.read()
    
KEYWORDS = ('protobuf pdns receiver json')

setuptools.setup(
    name="pdns_protobuf_receiver",
    version=VERSION,
    author="Denis MACHARD",
    author_email="d.machard@gmail.com",
    description="Python PDNS protobuf receiver to JSON stream",
    long_description=LONG_DESCRIPTION,
    long_description_content_type="text/markdown",
    url="https://github.com/dmachard/pdns-protobuf-receiver",
    packages=['pdns_protobuf_receiver'],
    include_package_data=True,
    platforms='any',
    keywords=KEYWORDS,
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Libraries",
    ],
    entry_points={'console_scripts': ['pdns_protobuf_receiver = pdns_protobuf_receiver.receiver:start_receiver']},
    install_requires=[
        "dnspython",
        "protobuf"
    ]
)
