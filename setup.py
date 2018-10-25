import setuptools

setuptools.setup(
    name="robotframework-excellentlibrary",
    version="0.3",
    author="Bart Kleijngeld",
    author_email="bartkl@gmail.com",
    description="Robot Framework library for using Zeep.",
    url="https://github.com/bartkl/robotframework-zeeplibrary",
    packages=setuptools.find_packages(),
    classifiers=(
        "Operating System :: OS Independent",
    ),
    install_requires="zeep>=2.5.0",
)
