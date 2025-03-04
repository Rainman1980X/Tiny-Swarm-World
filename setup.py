from setuptools import setup, find_packages

setup(
    name="infrastructure",
    version="0.1",
    packages=find_packages(where="docker"),
    package_dir={"": "."},
    include_package_data=True,
    install_requires=[],  # Optional: requirements.txt lesen lassen
)