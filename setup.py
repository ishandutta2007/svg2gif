from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="svg2gif",
    version="0.1.0",
    author="Ishan Dutta",
    description="A CLI tool to convert animated SVG files into optimized animated GIFs using Playwright and Pillow.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ishandutta2007/svg2gif",
    py_modules=["svg2gif"],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
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
