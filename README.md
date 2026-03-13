# ZhiruiSHEN-VLN

<details open>
<summary><b>🇨🇳 中文版本 (Chinese)</b></summary>

## 2026-03-12: Node 1 联调完成
* **进展**：成功在 Windows 宿主机的 Isaac Sim (Jazzy 启动器环境) 与 WSL 内部的 ROS 2 之间建立了底层通信桥梁。
* **测试**：通过 `teleop_twist_keyboard` 成功下发 `/cmd_vel` 跑通了小车的物理运动。
* **演示**：录制了联调成功的视频，保存在 `ROS 2_topic_stream.mp4`。
* **踩坑记录**：解决了 Windows/WSL 跨网段下 FastDDS 的共享内存通信死锁问题。

## 2026-03-13: Node 2 文献综述与模型选择完成
* **调研范围**：精读 2023–2026 年间 VLN 领域 5 篇核心论文，聚焦连续环境（VLN-CE）下的感知、记忆与决策机制。
* **核心文献**：覆盖空间映射（BEVBert）、内存效率（MapNav）、端到端控制（Uni-NaVid）、进度监控（Progress-Think）、持续学习（CMMR-VLN）五个技术维度。
* **模型选择**：确定构建**层次化语义增强 VLA 架构（HSA-VLM）**，集成 ASM 语义地图记忆层与 Uni-NaVid 流式决策层。
* **下一步**：启动节点 3，配置 Habitat-Sim 仿真环境并加载预训练权重。

</details>

<details>
<summary><b>🇬🇧 English Version</b></summary>

## 2026-03-12: Node 1 Integration Completed
* **Progress**: Successfully established the underlying communication bridge between Isaac Sim (Jazzy launcher environment) on the Windows host and ROS 2 inside WSL.
* **Testing**: Successfully verified the physical movement of the robot by publishing to `/cmd_vel` via `teleop_twist_keyboard`.
* **Demo**: Recorded a video demonstrating the successful integration, saved as `ROS 2_topic_stream.mp4`.
* **Troubleshooting**: Resolved the FastDDS shared memory communication deadlock issue across the Windows/WSL subnet boundaries.

## 2026-03-13: Node 2 Literature Review & Model Selection Completed
* **Survey Scope**: In-depth review of 5 core VLN papers (2023–2026), focusing on perception, memory, and decision-making in continuous environments (VLN-CE).
* **Key Papers**: Covering five technical dimensions — spatial mapping (BEVBert), memory efficiency (MapNav), end-to-end control (Uni-NaVid), progress monitoring (Progress-Think), and continual learning (CMMR-VLN).
* **Model Selection**: Decided to build a **Hierarchical Semantics-Augmented VLA architecture (HSA-VLM)**, integrating an ASM-based memory layer and Uni-NaVid's streaming action decoder.
* **Next Step**: Launch Node 3 — configure Habitat-Sim simulation environment and load pretrained weights.

</details>