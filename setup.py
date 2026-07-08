from setuptools import setup, find_packages
from pathlib import Path

# Read the contents of your README file
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding="utf-8")

setup(
    name='django-rest-pgtenants',
    version='0.1.0rc2',  # 🌟 Bump the version to rc2 so PyPI accepts the new upload
    description='A lightweight, native Django multi-tenant schema isolation framework.',
    long_description=long_description,          # 🌟 Passes your README content
    long_description_content_type='text/markdown', # 🌟 Tells PyPI it's written in Markdown
    author='Pankaj Jarial',
    packages=find_packages(include=['django_rest_pgtenants', 'django_rest_pgtenants.*']),
    install_requires=[
        'Django>=4.0',
        'djangorestframework',
        'djangorestframework-simplejwt',
    ],
    classifiers=[
        'Framework :: Django',
        'Programming Language :: Python :: 3',
    ],
)
