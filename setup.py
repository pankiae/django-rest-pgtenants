from setuptools import setup, find_packages
from pathlib import Path

# Read the contents of your README file
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding="utf-8")

setup(
    name='django-rest-pgtenants',
    version='0.1.0',
    description='A lightweight, API-first Django & Django REST Framework (DRF) multi-tenancy schema isolation package.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Pankaj Jarial',
    packages=find_packages(include=['django_rest_pgtenants', 'django_rest_pgtenants.*']),
    install_requires=[
        'Django>=4.0',
        'djangorestframework',
        'djangorestframework-simplejwt',
    ],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Framework :: Django',
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
)
