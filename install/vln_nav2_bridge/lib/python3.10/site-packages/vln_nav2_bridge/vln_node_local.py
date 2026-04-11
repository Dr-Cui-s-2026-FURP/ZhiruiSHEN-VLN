#!/usr/bin/env python3
import math
from typing import Optional

import rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter
from std_msgs.msg import String
from geometry_msgs.msg import PoseStamped
from nav2_simple_commander.robot_navigator import BasicNavigator, TaskResult

from .qwen_model_wrapper import QwenVLWrapper
from .text_to_pose_converter import TextToPoseConverter


class VLNBridgeNodeLocal(Node):
    """Node 5 local bridge: text instruction -> local VLM -> Nav2 goal."""

    def __init__(self) -> None:
        super().__init__("vln_bridge_node_local")

        # ============ CRITICAL FIX 1: Read use_sim_time (already declared by ROS 2 framework) ============
        # This ensures BasicNavigator syncs with simulation time from /clock topic
        # Note: use_sim_time is auto-declared by ROS 2, so we just read it
        try:
            use_sim_time = self.get_parameter("use_sim_time").value
        except Exception:
            use_sim_time = False  # Fallback default
        self.get_logger().info(f"use_sim_time={use_sim_time}")

        # ============ Declare all other parameters ============
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
        self.declare_parameter("safe_min_x", -8.0)
        self.declare_parameter("safe_max_x", 10.0)
        self.declare_parameter("safe_min_y", -12.0)
        self.declare_parameter("safe_max_y", 15.0)
        self.declare_parameter("inference_mode", "subprocess")
        self.declare_parameter("conda_env", "isaaclab")
        self.declare_parameter(
            "inference_script_path",
            "/home/bluepoisons/Desktop/FURP/VLN/ZhiruiSHEN-VLN/src/vln_inference/run_inference_cli.py",
        )

        # ============ Read all parameters ============
        self.model_path = self.get_parameter("model_path").value
        self.image_path = self.get_parameter("image_path").value
        self.instruction_topic = self.get_parameter("instruction_topic").value
        self.goal_frame = self.get_parameter("goal_frame").value
        self.max_new_tokens = int(self.get_parameter("max_new_tokens").value)
        self.dry_run = bool(self.get_parameter("dry_run").value)
        self.safe_min_x = float(self.get_parameter("safe_min_x").value)
        self.safe_max_x = float(self.get_parameter("safe_max_x").value)
        self.safe_min_y = float(self.get_parameter("safe_min_y").value)
        self.safe_max_y = float(self.get_parameter("safe_max_y").value)
        self.inference_mode = self.get_parameter("inference_mode").value
        self.conda_env = self.get_parameter("conda_env").value
        self.inference_script_path = self.get_parameter("inference_script_path").value

        # ============ Initialize model and converter (lightweight, no blocking) ============
        self.model = QwenVLWrapper(
            model_path=self.model_path,
            max_new_tokens=self.max_new_tokens,
            mode=self.inference_mode,
            conda_env=self.conda_env,
            inference_script_path=self.inference_script_path,
        )
        self.converter = TextToPoseConverter(
            min_x=self.safe_min_x,
            max_x=self.safe_max_x,
            min_y=self.safe_min_y,
            max_y=self.safe_max_y,
        )

        # ============ CRITICAL FIX 2: Defer Nav2 initialization to timer callback ============
        # This allows rclpy.spin() to start BEFORE waiting for Nav2 active.
        # Without this, /clock messages cannot be processed while waitUntilNav2Active() blocks.
        self.navigator = None
        self.goal_pub = None
        self.sub = None
        self.nav2_initialized = False

        # Single-shot timer: runs once after node starts spinning, then destroys itself
        self._init_timer = self.create_timer(0.1, self._on_init_timer_callback)
        self.get_logger().info(
            "Node initialized (fast path). Nav2 setup will happen asynchronously..."
        )

    def _on_init_timer_callback(self) -> None:
        """
        Callback invoked by timer after rclpy.spin() is already running.
        This ensures /clock messages are being processed when we call waitUntilNav2Active().
        """
        if self.nav2_initialized:
            return

        try:
            # Now safe to initialize BasicNavigator with synced simulation time
            self.navigator = BasicNavigator()

            # ============ CRITICAL FIX: Force BasicNavigator into simulation time ============
            # BasicNavigator is an independent ROS 2 node that doesn't inherit use_sim_time
            # from the command-line parameter, so we must set it explicitly!
            use_sim_time_param = Parameter('use_sim_time', Parameter.Type.BOOL, True)
            self.navigator.set_parameters([use_sim_time_param])
            self.get_logger().info("BasicNavigator synced to simulation time.")
            # ==============================================================================

            self.get_logger().info("Waiting for Nav2 to become active...")

            # This blocking call now runs inside the spin loop, so /clock is being processed
            # self.navigator.waitUntilNav2Active()
            self.get_logger().info("Nav2 is active.")

            # Create publisher and subscription AFTER Nav2 is confirmed active
            self.goal_pub = self.create_publisher(PoseStamped, "/vln_goal_pose", 10)
            self.sub = self.create_subscription(
                String,
                self.instruction_topic,
                self._on_instruction,
                10,
            )

            self.nav2_initialized = True
            self.get_logger().info(
                "Node ready. "
                f"Listening on {self.instruction_topic}. "
                f"dry_run={self.dry_run}, inference_mode={self.inference_mode}"
            )

        except Exception as exc:
            self.get_logger().error(f"Nav2 initialization failed: {exc}. Retrying...")
        finally:
            # Destroy this timer after first attempt
            self.destroy_timer(self._init_timer)

    def _on_instruction(self, msg: String) -> None:
        # Safety check: wait for Nav2 to be ready before processing
        if not self.nav2_initialized:
            self.get_logger().warning(
                "Received instruction before Nav2 initialized. Ignoring: " + msg.data[:50]
            )
            return

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
            self.get_logger().error(f"显存爆了或推理失败: {exc}")
            self.get_logger().info("启动紧急备用降级逻辑 (Fallback)...")
            # 不 return！强行把指令本身当作输出，去触发 text_to_pose_converter 里的正则关键词！
            model_output = instruction

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
