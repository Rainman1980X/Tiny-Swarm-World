from setuptools import setup, find_packages


setup(
    name="tiny-swarm-world",
    version="0.1",
    packages=find_packages(where="docker"),
    package_dir={"": "docker"},
    include_package_data=True,
    install_requires=[],
)

