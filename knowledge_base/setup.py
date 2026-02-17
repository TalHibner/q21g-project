from setuptools import setup

setup(
    name="knowledge_base",
    version="0.1",
    packages=["knowledge_base"],
    package_dir={"knowledge_base": "."},
    install_requires=[
        "pdfplumber>=0.10.0",
        "chromadb>=0.4.0",
        "sentence-transformers>=2.2",
    ],
)
