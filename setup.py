from setuptools import setup, find_packages

setup(
    name="svg2gif",
    version="0.1.0",
    py_modules=["svg2gif"],
    install_requires=[
        "Pillow>=9.0.0",
        "playwright>=1.20.0",
    ],
    entry_points={
        "console_scripts": [
            "svg2gif=svg2gif:main",
        ],
    },
)
