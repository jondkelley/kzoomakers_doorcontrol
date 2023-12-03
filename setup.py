# Filename    : setup.py
# Author      : Jon Kelley <jonk@omg.lol>
# Description : Door Access Control Software

from setuptools import setup, find_packages
from sys import path
from os import environ

path.insert(0, '.')

NAME = "doorcontrol"

if __name__ == "__main__":

    setup(
        name=NAME,
        version='0.0.4',
        author="Jonathan Kelley",
        author_email="jon.kelley@kzoomakers.org",
        url="https://github.com/jondkelley/",
        license='ASLv2',
        packages=find_packages(),
        include_package_data=True,
        package_dir={NAME: NAME},
        description="doorcontrol - kzoomakers.org",
        install_requires=['Flask==2.3.0', 'werkzeug==2.3.0', 'requests', 'unidecode', 'Flask-Session', 'python-dateutil', 'flask-login'],
        entry_points={
            'console_scripts': ['doorcontrol = doorctl.runserver:main'],
        },
        zip_safe=False,
    )
