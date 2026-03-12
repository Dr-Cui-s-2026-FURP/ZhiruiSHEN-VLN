# ZhiruiSHEN-VLN

[中文](README.md) | English

## 2026-03-12: Node 1 Integration Completed
* **Progress**: Successfully established the low-level communication bridge between Isaac Sim (Jazzy launcher environment) on the Windows host and ROS 2 running inside WSL.
* **Test**: Verified robot motion by publishing `/cmd_vel` through `teleop_twist_keyboard`.
* **Demo**: Recorded a successful integration demo video at `ROS 2_topic_stream.mp4`.
* **Issue Resolved**: Fixed a FastDDS shared-memory deadlock issue in a cross-subnet Windows/WSL setup.
