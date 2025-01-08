from setuptools import setup, find_packages

with open("requirements.txt") as f:
	install_requires = f.read().strip().split("\n")

# get version from __version__ variable in core/__init__.py
from core import __version__ as version

setup(
	name="core",
	version=version,
	description="Core ERP System for Agnikul Cosmos",
	author="Agnikul Cosmos Private Limited",
	author_email="automationbot@agnikul.in",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
