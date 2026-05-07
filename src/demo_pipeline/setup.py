from setuptools import find_packages, setup

package_name = "demo_pipeline"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(),
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
        (f"share/{package_name}/launch", ["launch/demo_ros2.launch.py"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="ron",
    maintainer_email="ron@example.com",
    description="ROS2 adapters for the nuScenes offline demo.",
    license="MIT",
    entry_points={
        "console_scripts": [
            "nuscenes_replay_node = demo_pipeline.nuscenes_replay_node:main",
            "adas_gt_adapter_node = demo_pipeline.adas_gt_adapter_node:main",
            "dms_scripted_node = demo_pipeline.dms_scripted_node:main",
            "iqa_adapter_node = demo_pipeline.iqa_adapter_node:main",
            "render_recorder_node = demo_pipeline.render_recorder_node:main",
        ],
    },
)
