from glob import glob
from setuptools import find_packages, setup

package_name = "signal_gateway"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        ("share/" + package_name + "/config", glob("config/*.yaml")),
        ("share/" + package_name + "/launch", glob("launch/*.launch.py")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="ron",
    maintainer_email="ron@example.com",
    description="AutoDriveLab package: " + package_name,
    license="MIT",
    tests_require=["pytest"],
    entry_points={"console_scripts": ["mock_gateway_node = signal_gateway.mock_gateway_node:main"]},
)
