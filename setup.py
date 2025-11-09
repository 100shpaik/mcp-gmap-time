from setuptools import setup, find_packages

setup(
    name="mcp-drive-time-plotter",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "mcp>=1.7.1",
        "python-dotenv>=1.0.1",
        "requests>=2.32.3",
        "plotext>=5.2.8",
        "rich>=13.9.2",
        "click>=8.1.7",
    ],
    python_requires=">=3.10",
)
