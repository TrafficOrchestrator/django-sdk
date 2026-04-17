from setuptools import setup, find_packages

setup(
    name="traffic-orchestrator-django",
    version="2.0.0",
    description="Official Django integration for Traffic Orchestrator license validation",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Traffic Orchestrator",
    author_email="support@trafficorchestrator.com",
    url="https://trafficorchestrator.com/docs/sdks/django",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "django>=3.2",
        "requests>=2.28",
    ],
    extras_require={
        "offline": ["PyJWT>=2.0", "cryptography>=3.0"],
    },
    classifiers=[
        "Framework :: Django",
        "Framework :: Django :: 4.0",
        "Framework :: Django :: 5.0",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
    ],
    keywords="licensing license-validation traffic-orchestrator django",
    license="MIT",
)
