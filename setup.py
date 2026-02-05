from setuptools import setup, find_packages

setup(
    name="SIK-Radio-Configurator",
    version="1.0.0",
    description="Configuration tool for Holybro/RFD900 SIK radios - similar to Mission Planner",
    author="SIK Radio Team",
    packages=find_packages(),
    install_requires=[
        'pyserial>=3.5',
        'PyQt6>=6.0.0',
    ],
    entry_points={
        'console_scripts': [
            'sik-configurator=src.gui.main:main',
        ],
    },
    python_requires='>=3.8',
)
