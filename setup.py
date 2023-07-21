from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="exorde",
    version="v2.3.4",
    author="Exorde Labs",
    author_email="hello@exordelabs.com",
    description="The AI-based client to mine data and power the Exorde Network",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/exorde-labs/exorde-client",
    entry_points={"console_scripts": ["exorde = exorde.main:run"]},
    packages=find_packages(include=["exorde"]),
    include_package_data=True,
    install_requires=[
        "madtypes",
        "eth-account",
        "asyncio",
        "aiohttp",
        "lxml",
        "HTMLParser",
        "pytz",
        "pyyaml",
        "web3",
        "packaging",
        "numpy==1.23.4",
        "tiktoken==0.4.0",
        "feedparser==6.0.8",
        "python_dateutil==2.8.2",
        "newspaper3k==0.2.8",
        "fasttext==0.9.2",
        "fasttext-langdetect==1.0.5",
        "huggingface_hub==0.14.1",
        "pandas==1.5.3",
        "sentence-transformers==2.2.2",
        "spacy==3.5.1",
        "swifter==1.3.4",
        "tensorflow==2.12.0",
        "torch==1.13.0",
        "vaderSentiment==3.3.2",
        "yake==0.4.8",
        "argostranslate==1.8.0",
        "wtpsplit==1.2.3"
    ],
    python_requires=">=3.10",
)
