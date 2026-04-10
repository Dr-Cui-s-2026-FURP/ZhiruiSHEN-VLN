from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    return LaunchDescription(
        [
            Node(
                package="vln_nav2_bridge",
                executable="vln_node_local",
                name="vln_bridge_node_local",
                output="screen",
                parameters=[
                    {"use_sim_time": True},
                ],
            )
        ]
    )
