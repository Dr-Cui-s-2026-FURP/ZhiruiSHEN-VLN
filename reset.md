# Isaac Lab + ROS 2 联调：重启后操作手册

## TIPS
- 跑 Isaac Lab 相关脚本：必须先 `conda activate isaaclab`。
- 跑 Nav2/ROS 2 官方节点：不要进 Conda，只用系统 ROS 环境。

## 需要开哪些终端

### 终端 0（需要 Conda）：启动 Isaac Sim
```bash
conda activate isaaclab
cd ~/Desktop/FURP/VLN_usd
python scripts/isaaclab_vln_launcher.py
```
界面出来后，点击 Play。

### 终端 6（需要 Conda）：启动 Node 4（Qwen/GLM）
```bash
conda activate isaaclab
source /opt/ros/humble/setup.bash
python your_qwen_node4.py
```

### 终端 1（不要 Conda）：查看 /clock
```bash
source /opt/ros/humble/setup.bash
ros2 topic echo /clock | grep sec
```

### 终端 2（不要 Conda）：点云转激光
```bash
source /opt/ros/humble/setup.bash
ros2 run pointcloud_to_laserscan pointcloud_to_laserscan_node ...
```

### 终端 3（不要 Conda）：启动 Nav2
```bash
source /opt/ros/humble/setup.bash
ros2 launch nav2_bringup bringup_launch.py use_sim_time:=True map:=...
```

### 终端 4（不要 Conda）：发布静态 TF
```bash
source /opt/ros/humble/setup.bash
ros2 run tf2_ros static_transform_publisher 0 0 0 0 0 0 map odom
```

### 终端 5（不要 Conda）：打开 RViz2
```bash
source /opt/ros/humble/setup.bash
rviz2 -d ...
```

## 快速判断
- 要用 `isaaclab` 包或仿真器：进 Conda。
- 只跑 ROS 2 官方节点、看 topic、开 RViz：不进 Conda。

## 出错时怎么做
- `ImportError: No module named 'rclpy'`：你在 Conda 里跑了 ROS 命令。先 `conda deactivate`，再重试。
- `ModuleNotFoundError: No module named 'isaaclab'`：你没激活 `isaaclab` 环境。
- `Detected jump back in time`：去终端 4 运行 static tf 命令。
