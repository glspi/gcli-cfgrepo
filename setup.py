import setuptools

__version__ = "0.0.1"

with open("requirements.txt", "r", encoding="utf-8") as f:
    INSTALL_REQUIRES = f.read().splitlines()

setuptools.setup(
    name="gcli-cfgrepo",
    version=__version__,
    packages=["cfgrepo_builder"],
    install_requires=INSTALL_REQUIRES,
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Operating System :: MacOS",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3 :: Only",
    ],
    python_requires=">=3.7",
    entry_points={"console_scripts": ["cfgrepo = cfgrepo_builder.cfgrepo_builder:app"]},
)