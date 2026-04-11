# Node 3 稳定运行手册 (2026-04-11 版)

## 第一部：物理超度

在启动任何东西之前，必须在一个终端里执行以下命令。这会清理掉被 `Ctrl+Z` 挂起的僵尸进程和锁死的共享内存端口。

```bash
# 强杀所有相关进程
killall -9 ros2 rviz2 component_container component_container_isolated
# 清理 FastDDS 锁死的共享内存 (解决 RTPS_TRANSPORT_SHM Error 的核心)
rm -rf /dev/shm/fastrtps_port*
# 重启 ROS 2 守护进程
ros2 daemon stop && ros2 daemon start
```

---

## 第二步：五终端启动流 (按顺序执行)

### 终端 1：激活物理世界 (Isaac Sim)
**环境：Conda**

```bash
conda activate isaaclab
cd ~/Desktop/FURP/VLN_usd
python scripts/isaaclab_vln_launcher.py
```
👉 **动作**：等待界面加载后，点击顶部的 **Play (▶️)**。

### 终端 2：点云转激光 (压缩 3D)
**环境：原生 ROS**

```bash
source /opt/ros/humble/setup.bash
ros2 run pointcloud_to_laserscan pointcloud_to_laserscan_node --ros-args -p use_sim_time:=True
```

### 终端 3：启动导航与地图服务器 (Bringup)
**环境：原生 ROS**

注意：这里使用了你确认的 `/data/` 路径。

```bash
source /opt/ros/humble/setup.bash
ros2 launch nav2_bringup bringup_launch.py \
    use_sim_time:=True \
    autostart:=True \
    map:=/home/bluepoisons/Desktop/FURP/VLN/ZhiruiSHEN-VLN/data/warehouse_map.yaml
```

### 终端 4：坐标桥梁 (那个被遗忘的 odom 转换)
**环境：原生 ROS**

没有这个，Nav2 会一直报 `Invalid frame ID "odom"`。

```bash
source /opt/ros/humble/setup.bash
ros2 run tf2_ros static_transform_publisher 0 0 0 0 0 0 map odom --ros-args -p use_sim_time:=True
```

### 终端 5：独立弹出 RViz
**环境：原生 ROS**

```bash
source /opt/ros/humble/setup.bash
rviz2 -d /opt/ros/humble/share/nav2_bringup/rviz/nav2_default_view.rviz
```

---

## 调试秘籍

- **地图还是黑的？**：在 RViz 左侧面板点击 **Add** -> **By topic** -> 找到 `/map` 话题下的 **Map** 并添加。
- **退出程序**：**严禁使用 `Ctrl+Z`**，请务必使用 **`Ctrl+C`** 退出。如果误操作了，请回到“第一步”执行清理命令。
- **时间戳报错**：如果看到 `Jump back in time`，说明你重启了仿真器但没重启终端 2、3、4。请重启这三个终端以同步时间。

---

你可以把这段内容直接存成 `recovery.md`。现在按这个顺序去跑，Node 3 的大地图绝对能一秒跳出来。
