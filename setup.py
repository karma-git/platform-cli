import pathlib
from setuptools import find_packages, setup

# The directory containing this file


HERE = pathlib.Path(__file__).parent

setup(
    name="nx-pv-migrate",
    python_requires=">=3.8",
    version="0.1.3",
    py_modules=["libs"],
    packages=find_packages(exclude=()),
    include_package_data=True,
    install_requires=["requests", "kubernetes"],
    entry_points="""
        [console_scripts]
        nx-k8s=main:main
    """,
)
