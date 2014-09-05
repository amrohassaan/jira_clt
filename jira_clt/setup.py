from distutils.core import setup
from setuptools import find_packages

setup(
    name='jira_clt',
    author='Linaro.org',
    author_email='amro.hassaan@linaro.org',
    version='1.1',
    description="Linaro JIRA Command line tools",
    entry_points={
        'console_scripts': [
            'efforts=jira_clt.efforts:main']
    },
    install_requires=['jira-python==0.16', 'oauth2==1.5.211', 'pycrypto==2.6.1',
                      'workdays==1.3', 'configobj==5.0'],
    packages=find_packages(),
    include_package_data=True
)
