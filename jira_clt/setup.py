from distutils.core import setup
from setuptools import find_packages


setup(
    name='jira_clt',
    author='Linaro.org',
    author_email='amro.hassaan@linaro.org',
    url='https://github.com/amrohassaan/jira_clt',
    download_url='https://github.com/amrohassaan/jira_clt/tarball/1.2',
    version='1.2',
    description="Linaro JIRA Command line tools",
    entry_points={
        'console_scripts': [
            'efforts=jira_clt.efforts:main']
    },
    install_requires=['pycrypto==2.6.1', 'jira-python==0.31',
                      'workdays==1.3', 'configobj==5.0', 'python-dateutil==1.5'],
    packages=find_packages(),
    include_package_data=True
)
