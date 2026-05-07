from glob import glob
from setuptools import find_packages, setup


package_name = "dms_module"

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
    description="ROS2 driver monitoring system module.",
    license="MIT",
    tests_require=["pytest"],
    entry_points={"console_scripts": ["dms_node = dms_module.dms_node:main"]},
)
