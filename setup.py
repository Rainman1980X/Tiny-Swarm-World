from setuptools import setup, find_packages


setup(
    name="infra-core",
    version="0.1",
    packages=find_packages(where="."),  # Suche in allen Verzeichnissen
    package_dir={"": "."},  # Setze das Root-Verzeichnis als Basis
    include_package_data=True,
    install_requires=[],
)

