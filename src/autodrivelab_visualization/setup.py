from glob import glob
from setuptools import find_packages, setup

package_name = "autodrivelab_visualization"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml", "README.md"]),
        ("share/" + package_name + "/launch", glob("launch/*.launch.py")),
        ("share/" + package_name + "/rviz", glob("rviz/*.rviz")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="ron",
    maintainer_email="ron@example.com",
    description="RViz2 MarkerArray visualization for AutoDriveLab BEV objects.",
    license="MIT",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "bev_marker_node = autodrivelab_visualization.bev_marker_node:main",
            "test_bev_objects_publisher = autodrivelab_visualization.test_bev_objects_publisher:main",
        ],
    },
)
