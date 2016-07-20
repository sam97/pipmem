from setuptools import setup


def readme():
    with open('README.md') as f:
        return f.read()

setup(name='pipmem',
      version='0.3',
      description='Transaction logging wrapper for pip',
      long_description=readme(),
      classifiers=['Programming Language :: Python :: 3.5'],
      url='https://github.com/evitalis/pipmem',
      author='evitalis',
      packages=['pipmem'],
      install_requires=['pip', ],
      entry_points={'console_scripts': ['pipmem=pipmem.pipmem:main']},
      include_package_data=True,
      zip_safe=False)
