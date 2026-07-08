from setuptools import setup, find_packages

setup(
    name='django-rest-pgtenants',
    version='0.1.0rc1',  # 🌟 Changed to a pre-release version format
    description='A lightweight, native Django multi-tenant schema isolation framework.',
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
