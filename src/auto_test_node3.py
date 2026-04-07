#!/usr/bin/env python3
import rclpy
from geometry_msgs.msg import PoseStamped
from nav2_simple_commander.robot_navigator import BasicNavigator, TaskResult
import math
import time
import os
from datetime import datetime

def main():
    # 初始化 ROS 2
    rclpy.init()
    
    # 实例化 Nav2 简单指令器
    navigator = BasicNavigator()

    print("正在等待 Nav2 系统就绪...")
    navigator.waitUntilNav2Active()
    print("Nav2 已就绪！准备开始全自动测试。")

    # Node 3 要求: 10 次测试路线 (设置在 -4 到 4 的安全区间内，避免贴墙)
    test_goals = [
        [-3.0, -3.0, 0.0],    # 目标 1: 左下安全区
        [3.0, -3.0, 1.57],    # 目标 2: 右下安全区
        [3.0, 4.0, 3.14],     # 目标 3: 右上安全区
        [-3.0, 4.0, -1.57],   # 目标 4: 左上安全区
        [0.0, 0.0, 0.0],      # 目标 5: 中央原点
        [-2.0, -1.0, 0.78],   # 目标 6: 左侧中段
        [2.0, 1.0, -0.78],    # 目标 7: 右侧中段
        [-1.0, 3.0, 1.57],    # 目标 8: 顶部中段
        [1.0, -2.0, 3.14],    # 目标 9: 底部中段
        [0.0, 2.0, 0.0]       # 目标 10: 最终回归中心偏上
    ]

    success_count = 0
    
    # 准备日志文件目录和文件名
    log_dir = "/home/bluepoisons/Desktop/FURP/VLN/ZhiruiSHEN-VLN/data"
    os.makedirs(log_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = os.path.join(log_dir, f"node3_experiment_log_{timestamp}.txt")

    print("\n==================================")
    print("开始 Node 3 自动化测试 ")
    print("==================================")

    # 打开文件并开始记录
    with open(log_filename, "w", encoding="utf-8") as log_file:
        log_file.write(f"--- Node 3 实验日志 ---\n")
        log_file.write(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        for i, goal_coords in enumerate(test_goals):
            msg = f"▶️ 正在执行第 {i+1}/10 次测试: 目标坐标 [X: {goal_coords[0]}, Y: {goal_coords[1]}]"
            print(f"\n{msg}")
            log_file.write(msg + "\n")
            
            # 封装坐标数据
            goal_pose = PoseStamped()
            goal_pose.header.frame_id = 'map'
            goal_pose.header.stamp = navigator.get_clock().now().to_msg()
            goal_pose.pose.position.x = goal_coords[0]
            goal_pose.pose.position.y = goal_coords[1]
            
            # 将偏航角(Yaw)转换为四元数
            theta = goal_coords[2]
            goal_pose.pose.orientation.z = math.sin(theta / 2.0)
            goal_pose.pose.orientation.w = math.cos(theta / 2.0)

            # 下发目标
            navigator.goToPose(goal_pose)

            # 循环监控执行过程
            while not navigator.isTaskComplete():
                feedback = navigator.getFeedback()
                if feedback:
                    print(f"距离目标还有: {feedback.distance_remaining:.2f} 米...", end='\r')
                time.sleep(0.5)

            # 检查这次导航的结果
            result = navigator.getResult()
            if result == TaskResult.SUCCEEDED:
                result_msg = f"✅ 第 {i+1} 次测试：成功到达目标！"
                success_count += 1
            elif result == TaskResult.CANCELED:
                result_msg = f"⚠️ 第 {i+1} 次测试：导航被取消。"
            elif result == TaskResult.FAILED:
                result_msg = f"❌ 第 {i+1} 次测试：导航失败。"
            
            print(f"\n{result_msg}")
            log_file.write(result_msg + "\n\n")

            time.sleep(2.0) # 每次测试完停顿 2 秒，让系统状态稳定

        # 输出最终的实验报告
        final_report = (
            "==================================\n"
            f"🎉 测试结束！最终成功率: {success_count}/{len(test_goals)} ({(success_count/len(test_goals))*100}%)\n"
            "=================================="
        )
        print(f"\n{final_report}")
        log_file.write(final_report + "\n")

    print(f"\n 实验日志已成功保存至: {log_filename}")
    rclpy.shutdown()

if __name__ == '__main__':
    main()