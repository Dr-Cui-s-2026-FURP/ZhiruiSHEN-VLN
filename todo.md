# Node 5 使用说明

Node 5 现在不是单独跑一个 `your_qwen_node4.py`，而是一个 ROS 2 桥接节点。它的职责是：接收自然语言指令，调用本地 Qwen3-VL-2B 推理，再把结果转换成 Nav2 可执行的目标点。

## 先启动基础环境

### 终端 1：Isaac Sim
```bash
conda activate isaaclab
isaacsim
```

### 终端 2：静态 TF
```bash
source /opt/ros/humble/setup.bash
ros2 run tf2_ros static_transform_publisher 0 0 0 0 0 0 map odom --ros-args -p use_sim_time:=True
```

### 终端 3：点云转激光
```bash
source /opt/ros/humble/setup.bash
ros2 run pointcloud_to_laserscan pointcloud_to_laserscan_node --ros-args -p use_sim_time:=True
```

### 终端 4：Nav2
```bash
source /opt/ros/humble/setup.bash
ros2 launch nav2_bringup bringup_launch.py use_sim_time:=True autostart:=True map:=/home/bluepoisons/Desktop/FURP/VLN/ZhiruiSHEN-VLN/data/warehouse_map.yaml rviz:=True
```

## 启动 Node 5

```bash
conda activate isaaclab
source /opt/ros/humble/setup.bash
cd /home/bluepoisons/Desktop/FURP/VLN/ZhiruiSHEN-VLN
source install/setup.bash
ros2 run vln_nav2_bridge vln_node_local --ros-args -p use_sim_time:=True
```

## 下发指令

```bash
source /opt/ros/humble/setup.bash
cd /home/bluepoisons/Desktop/FURP/VLN/ZhiruiSHEN-VLN
source install/setup.bash
ros2 topic pub /vln_instruction std_msgs/msg/String "{data: 'Go to the right shelf with purple boxes'}" -1
```

## 常用调试

- 先把 `dry_run` 改成 `True`，确认指令、模型输出和坐标解析没问题，再改回 `False` 真正导航。
- 如果报 `ImportError: No module named 'rclpy'`，先检查是否执行了 `source /opt/ros/humble/setup.bash` 和 `source install/setup.bash`。
- 如果报 `Detected jump back in time`，重启终端 2、3、4，让它们重新同步仿真时间。

