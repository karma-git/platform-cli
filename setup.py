import pathlib
from setuptools import find_packages, setup

# The directory containing this file


HERE = pathlib.Path(__file__).parent

setup(
    name="platform_cli",
    python_requires=">=3.10",
    version="0.3.0",
    packages=find_packages(exclude=()),
    include_package_data=True,
    package_data={
        'platform_cli': ['lib/yaml/*.yml'],
    },
    install_requires=[
        "requests==2.28.1",
        "kubernetes==25.3.0",
        "pydantic==1.10.2",
        "emoji==2.2.0",
        ""
    ],
    entry_points={
        "console_scripts": ['pl-cli=platform_cli.runner:run'],
    },
)
