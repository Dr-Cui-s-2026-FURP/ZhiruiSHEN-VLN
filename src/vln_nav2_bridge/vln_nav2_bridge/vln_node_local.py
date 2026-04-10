#!/usr/bin/env python3
import math
from typing import Optional

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from geometry_msgs.msg import PoseStamped
from nav2_simple_commander.robot_navigator import BasicNavigator, TaskResult

from .qwen_model_wrapper import QwenVLWrapper
from .text_to_pose_converter import TextToPoseConverter


class VLNBridgeNodeLocal(Node):
    """Node 5 local bridge: text instruction -> local VLM -> Nav2 goal."""

    def __init__(self) -> None:
        super().__init__("vln_bridge_node_local")

        self.declare_parameter(
            "model_path",
            "/home/bluepoisons/Desktop/FURP/VLN/models/Qwen3-VL-2B-Instruct",
        )
        self.declare_parameter(
            "image_path",
            "/home/bluepoisons/Desktop/FURP/VLN/ZhiruiSHEN-VLN/data/test_samples/warehouse_photo1.png",
        )
        self.declare_parameter("instruction_topic", "/vln_instruction")
        self.declare_parameter("goal_frame", "map")
        self.declare_parameter("max_new_tokens", 256)
        self.declare_parameter("dry_run", False)
        self.declare_parameter("safe_min_xy", -3.0)
        self.declare_parameter("safe_max_xy", 4.0)

        self.model_path = self.get_parameter("model_path").value
        self.image_path = self.get_parameter("image_path").value
        self.instruction_topic = self.get_parameter("instruction_topic").value
        self.goal_frame = self.get_parameter("goal_frame").value
        self.max_new_tokens = int(self.get_parameter("max_new_tokens").value)
        self.dry_run = bool(self.get_parameter("dry_run").value)
        self.safe_min_xy = float(self.get_parameter("safe_min_xy").value)
        self.safe_max_xy = float(self.get_parameter("safe_max_xy").value)

        self.model = QwenVLWrapper(
            model_path=self.model_path,
            max_new_tokens=self.max_new_tokens,
        )
        self.converter = TextToPoseConverter(
            min_xy=self.safe_min_xy,
            max_xy=self.safe_max_xy,
        )

        self.navigator = BasicNavigator()
        self.get_logger().info("Waiting for Nav2 to become active...")
        self.navigator.waitUntilNav2Active()
        self.get_logger().info("Nav2 is active.")

        self.goal_pub = self.create_publisher(PoseStamped, "/vln_goal_pose", 10)
        self.sub = self.create_subscription(
            String,
            self.instruction_topic,
            self._on_instruction,
            10,
        )

        self.get_logger().info(
            f"Node ready. Listening on {self.instruction_topic}. dry_run={self.dry_run}"
        )

    def _on_instruction(self, msg: String) -> None:
        instruction = msg.data.strip()
        if not instruction:
            self.get_logger().warning("Received empty instruction. Ignoring.")
            return

        self.get_logger().info(f"Received instruction: {instruction}")

        try:
            model_output = self.model.infer_goal_text(
                instruction=instruction,
                image_path=self.image_path,
            )
        except Exception as exc:
            self.get_logger().error(f"Model inference failed: {exc}")
            return

        self.get_logger().info(f"Model output: {model_output}")
        parsed = self.converter.convert(instruction=instruction, model_output=model_output)
        if not parsed.get("ok"):
            self.get_logger().warning(f"Conversion failed: {parsed.get('reason')}")
            return

        x = float(parsed["x"])
        y = float(parsed["y"])
        yaw = float(parsed["yaw"])
        method = parsed.get("method", "unknown")
        self.get_logger().info(
            f"Resolved target ({method}): x={x:.2f}, y={y:.2f}, yaw={yaw:.2f}"
        )

        pose = self._build_pose(x=x, y=y, yaw=yaw)
        self.goal_pub.publish(pose)
        self.get_logger().info("Published pose to /vln_goal_pose")

        if self.dry_run:
            self.get_logger().info("dry_run=True, skipping goToPose call.")
            return

        self.navigator.goToPose(pose)
        while not self.navigator.isTaskComplete():
            feedback = self.navigator.getFeedback()
            if feedback:
                self.get_logger().info(
                    f"Distance remaining: {feedback.distance_remaining:.2f} m"
                )

        result = self.navigator.getResult()
        if result == TaskResult.SUCCEEDED:
            self.get_logger().info("Navigation succeeded.")
        elif result == TaskResult.CANCELED:
            self.get_logger().warning("Navigation canceled.")
        elif result == TaskResult.FAILED:
            self.get_logger().error("Navigation failed.")
        else:
            self.get_logger().warning("Navigation returned unknown result.")

    def _build_pose(self, x: float, y: float, yaw: float) -> PoseStamped:
        pose = PoseStamped()
        pose.header.frame_id = self.goal_frame
        pose.header.stamp = self.navigator.get_clock().now().to_msg()
        pose.pose.position.x = x
        pose.pose.position.y = y
        pose.pose.orientation.z = math.sin(yaw / 2.0)
        pose.pose.orientation.w = math.cos(yaw / 2.0)
        return pose


def main(args: Optional[list] = None) -> None:
    rclpy.init(args=args)
    node = VLNBridgeNodeLocal()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
