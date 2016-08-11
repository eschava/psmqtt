from codecs import open
from os import path
from setuptools import setup
# To use a consistent encoding
here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='psmqtt',
    packages=['psmqtt'],
    package_data={'psmqtt': ['psmqtt.conf']},
    version='0.0.1',  # Semantic Versioning

    description='Utility reporting system health and status via MQTT',
    long_description=long_description,
    author='Eugene Schava',
    license='MIT',
    keywords='mqtt monitoring',
    install_requires=[
        'recurrent', 'paho-mqtt', 'python-dateutil', 'psutil', 'jinja2'],
    scripts=['bin/psmqtt']
)
