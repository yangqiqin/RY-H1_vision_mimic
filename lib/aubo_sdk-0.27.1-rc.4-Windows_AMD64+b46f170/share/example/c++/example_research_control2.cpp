#include <math.h>
#include <iostream>

#include <stdlib.h>
#ifdef WIN32
#include <Windows.h>
#else
#include <unistd.h>
#endif
#include <chrono>

#include "aubo_sdk/rpc.h"

#include "research_interface/robot.h"
#include "trajectory_io.h"
#include <csignal>
static volatile std::sig_atomic_t g_stop = 0;

static void on_sigint(int)
{
    g_stop = 1;
}

template <typename T, std::size_t N>
inline std::ostream &operator<<(std::ostream &os, const std::array<T, N> &list)
{
    for (size_t i = 0; i < list.size(); i++) {
        os << list.at(i);
        if (i != (list.size() - 1)) {
            os << ",";
        }
    }
    return os;
}

template <typename T, std::size_t N>
inline auto operator*(const std::array<T, N> &l, T x)
{
    std::array<T, N> temp;
    for (size_t i = 0; i < l.size(); i++) {
        temp[i] = l[i] * x;
    }
    return temp;
}

using namespace arcs::research_interface;
int examplePositionControl(Robot robot, bool &finish, bool loop)
{
    int ret = robot.setServoMode(
        static_cast<int>(arcs::aubo_sdk::JointServoModeType::Position));
    if (ret < 0) {
        std::cout << "setServoMode failed. " << std::endl;
        return -1;
    }
    // record6为5ms轨迹,record7为1ms轨迹
    TrajectoryIo traj_io("../trajs/record6.offt");
    auto trajs = traj_io.parse();
    if (trajs.empty()) {
        std::cout << "traj failed" << std::endl;
        return -1;
    }
    int index = 0;
    // 移动到第一个点
    JointPositions jnt_pos;
    for (int i = 0; i < 6; i++) {
        jnt_pos.q[i] = trajs[index][i];
    }

    std::cout << "movej: " << jnt_pos.q * (180. / M_PI) << std::endl;
    if (robot.movej(jnt_pos) < 0) {
        return -1;
    }

    // 开始记录(储存至 arcs_ws/log/.trace/ 下)
    auto csv_file = "research_control2.csv";
    robot.startRecord(csv_file);

    while (!finish) {
        robot.read([](const RobotState &robot_state) {
            std::cout << "read ===> q: " << robot_state.q * (180. / M_PI)
                      << std::endl;

            return true;
        });

        // 执行离线轨迹
        robot.control(
            [&](const RobotState &robot_state, double duration) {
                JointPositions jnt_pos;
                // Ctrl+C 请求退出 & 机械臂状态出现了问题时，让 control
                // 自然收尾退出
                if (g_stop || robot_state.error_code) {
                    jnt_pos.finished = true;
                    finish = true;
                    return jnt_pos;
                }

                for (int i = 0; i < 6; i++) {
                    jnt_pos.q[i] = trajs[index][i];
                }
                index++;
                if (index >= trajs.size() && loop) {
                    // 无限循环跑离线轨迹
                    index = 0;
                } else if (index >= trajs.size() && !loop) {
                    // 只跑一次离线轨迹
                    jnt_pos.finished = true;
                    finish = true;
                }
                return jnt_pos;
            },
            false, 0, false);
        if (!loop) {
            finish = true;
        }
    }

    // 停止记录
    robot.stopRecord();
    return 0;
}

int exampleVelocityControl(Robot robot, bool &finish, bool loop)
{
    int ret = robot.setServoMode(
        static_cast<int>(arcs::aubo_sdk::JointServoModeType::Velocity));
    if (ret < 0) {
        std::cout << "setServoMode failed. " << std::endl;
        return -1;
    }

    // record8为5ms轨迹,record9为40ms轨迹
    TrajectoryIo traj_io("../trajs/record8.offt");
    auto trajs = traj_io.parse();
    if (trajs.empty()) {
        std::cout << "traj failed" << std::endl;
        return -1;
    }
    int index = 0;
    // 移动到零点
    std::cout << "正在移动到零点. " << std::endl;
    JointPositions jnt_pos;
    jnt_pos.q = { 0.0, 0.0, 0.0, 0.0, 0.0, 0.0 };
    if (robot.movej(jnt_pos) < 0) {
        return -1;
    }

    // 开始记录(储存至 arcs_ws/log/.trace/ 下)
    auto csv_file = "research_control2.csv";
    robot.startRecord(csv_file);

    while (!finish) {
        robot.read([](const RobotState &robot_state) {
            std::cout << "read ===> q: " << robot_state.q * (180. / M_PI)
                      << std::endl;

            return true;
        });

        // 执行离线轨迹
        robot.veloControl(
            [&](const RobotState &robot_state, double duration) {
                JointSpeeds jnt_velo;
                // Ctrl+C 请求退出 & 机械臂状态出现了问题时，让 control
                // 自然收尾退出
                if (g_stop || robot_state.error_code) {
                    jnt_velo.finished = true;
                    finish = true;
                    return jnt_velo;
                }

                for (int i = 0; i < 6; i++) {
                    jnt_velo.qd[i] = trajs[index][i];
                }
                index++;
                if (index >= trajs.size() && loop) {
                    // 无限循环跑离线轨迹
                    index = 0;
                } else if (index >= trajs.size() && !loop) {
                    // 只跑一次离线轨迹
                    jnt_velo.finished = true;
                    finish = true;
                }
                return jnt_velo;
            },
            false, 0, false);
        if (!loop) {
            finish = true;
        }
    }

    // 停止记录
    robot.stopRecord();
    return 0;
}

int exampleCurrentControl(Robot robot, bool &finish, bool loop)
{
    robot.setServoMode(
        static_cast<int>(arcs::aubo_sdk::JointServoModeType::Current));

    // record10为5ms轨迹
    TrajectoryIo traj_io("../trajs/record10.offt");
    auto trajs = traj_io.parse();
    if (trajs.empty()) {
        std::cout << "traj failed" << std::endl;
        return -1;
    }
    int index = 0;
    // 移动到零点
    std::cout << "正在移动到零点. " << std::endl;
    JointPositions jnt_pos;
    jnt_pos.q = { 0.0, 0.0, 0.0, 0.0, 0.0, 0.0 };
    if (robot.movej(jnt_pos) < 0) {
        return -1;
    }

    // 开始记录(储存至 arcs_ws/log/.trace/ 下)
    auto csv_file = "research_control2.csv";
    robot.startRecord(csv_file);

    while (!finish) {
        robot.read([](const RobotState &robot_state) {
            std::cout << "read ===> q: " << robot_state.q * (180. / M_PI)
                      << std::endl;

            return true;
        });

        // 执行离线轨迹
        robot.currentControl(
            [&](const RobotState &robot_state, double duration) {
                JointCurrents jnt_curr;
                // Ctrl+C 请求退出 & 机械臂状态出现了问题时，让 control
                // 自然收尾退出
                if (g_stop || robot_state.error_code) {
                    jnt_curr.finished = true;
                    finish = true;
                    return jnt_curr;
                }

                for (int i = 0; i < 6; i++) {
                    jnt_curr.current[i] = trajs[index][i];
                }
                index++;
                if (index >= trajs.size() && loop) {
                    // 无限循环跑离线轨迹
                    index = 0;
                } else if (index >= trajs.size() && !loop) {
                    // 只跑一次离线轨迹
                    jnt_curr.finished = true;
                    finish = true;
                }
                return jnt_curr;
            },
            false, 0, false);
        if (!loop) {
            finish = true;
        }
    }

    // 停止记录
    robot.stopRecord();
    return 0;
}

int main(int argc, char *argv[])
{
    std::signal(SIGINT, on_sigint);

#ifdef SIGTERM
    // Linux
    std::signal(SIGTERM, on_sigint);
#endif

#ifdef SIGBREAK
    // MSVC
    std::signal(SIGBREAK, on_sigint);
#endif

    auto robot = Robot("10.0.0.1");

    // servo是否循环下发离线轨迹
    bool loop = false;

    // 离线轨迹是否完成或者机器人状态是否出错
    bool finish = false;

    // 位置环支持周期：1000/5000
    // 速度环支持周期：1000/5000的倍数
    int control_period = 5000;
    if (robot.setControlPeriod(control_period) < 0) {
        std::cout << "set Control Period failed" << std::endl;
        return -1;
    }

    // 如果机器人没有上电，对机器人进行上电操作
    if (robot.startup() < 0) {
        std::cout << "robot start up failed" << std::endl;
        return -1;
    }
    // 位置控制
    // examplePositionControl(robot, finish, loop);

    // 速度控制
    exampleVelocityControl(robot, finish, loop);

    // 电流控制
    // exampleCurrentControl(robot, finish, loop);

    return g_stop ? 130 : 0;
}
