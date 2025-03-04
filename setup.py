from setuptools import setup, find_packages

setup(
    name="infrastructure",
    version="0.1",
    packages=find_packages(where="docker"),  # Sucht nur in docker/
    package_dir={"": "docker"},  # Sagt setuptools, dass docker das Root-Modul ist
    include_package_data=True,
    install_requires=[],
)
