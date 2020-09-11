from setuptools import setup, find_packages

with open('requirements.txt') as reqs:
    install_requires = [
        line for line in reqs.read().split('\n')
        if (line and not line.startswith('--')) and (";" not in line)]

setup(
    name="circus_autorestart_plugin",
    version="0.0.1",
    license="BSD",
    url="https://github.com/metwork-framework/circus_autorestart_plugin",
    packages=find_packages(),
    install_requires=install_requires
)
