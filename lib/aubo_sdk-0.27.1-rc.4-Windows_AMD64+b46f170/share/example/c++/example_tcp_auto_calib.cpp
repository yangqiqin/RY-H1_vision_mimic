#include "aubo_sdk/rpc.h"
#include "aubo_sdk/rtde.h"

#include <robot_math/robot_math.h>

#include <array>
#include <atomic>
#include <chrono>
#include <cmath>
#include <iostream>
#include <mutex>
#include <stdexcept>
#include <string>
#include <thread>
#include <vector>
#include "skill_interface/tcp_auto_calib.h"

#ifdef WIN32
#include <Windows.h>
#endif

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

using namespace arcs::common_interface;
using namespace arcs::aubo_sdk;

constexpr const char *kRobotIp = "172.17.41.84";
constexpr int kRobotRpcPort = 30004;
constexpr int kRobotRtdePort = 30010;
constexpr const char *kUser = "aubo";
constexpr const char *kPassword = "123456";

void printPose(const std::vector<double> &v)
{
    std::cout << "[ ";
    for (int i = 0; i < v.size(); i++) {
        std::cout << v[i] << ", ";
    }
    std::cout << " ]" << std::endl;
}

int test01(RpcClientPtr rpc, RtdeClientPtr rtde_cli)
{
    try {
        rpc->setRequestTimeout(5000);
        rpc->connect(kRobotIp, kRobotRpcPort);
        if (!rpc->hasConnected()) {
            std::cerr << "RPC connect failed" << std::endl;
            return 1;
        }
        rpc->login(kUser, kPassword);
        if (!rpc->hasLogined()) {
            std::cerr << "RPC login failed" << std::endl;
            return 1;
        }

        // 接口调用: 连接到 RTDE 服务
        rtde_cli->connect(kRobotIp, kRobotRtdePort);
        // 接口调用: 登录
        rtde_cli->login(kUser, kPassword);

        TcpAutoCalib tcp_auto_calib(rpc, rtde_cli);

        //        auto result = tcp_auto_calib.calibrateSensorPoseWithTCP(1, 3);
        //        if (std::get<1>(result) != 0) {
        //            std::cout << "通过TCP标定传感器位置失败." << std::endl;
        //        } else {
        //            std::cout << "sensor_pose:";
        //            printPose(std::get<0>(result));
        //        }

        std::vector sensor_pose = { -0.564623, -0.0267271,  0.302365,
                                    -3.13986,  1.81117e-05, -1.26507 };
        auto result = tcp_auto_calib.tcpAutoCorrect(sensor_pose, 1, 3);
        if (std::get<1>(result) != 0) {
            std::cout << "TCP纠偏失败." << std::endl;
        } else {
            std::cout << "新的TCP:";
            printPose(std::get<0>(result));
        }

        //        auto result = tcp_auto_calib.tcpAutoCalibrate(1, 3);
        //        if (std::get<1>(result) != 0) {
        //            std::cout << "TCP自动标定失败." << std::endl;
        //        } else {
        //            std::cout << "TCP标定结果:";
        //            printPose(std::get<0>(result));
        //        }

        rtde_cli->logout();
        rtde_cli->disconnect();

        rpc->logout();
        rpc->disconnect();
    } catch (const std::exception &e) {
        std::cerr << "Exception: " << e.what() << std::endl;
        return 1;
    }
}

// 实现阻塞功能: 当机械臂运动到目标路点时，程序再往下执行
int waitArrival(RobotInterfacePtr impl)
{
    const int max_retry_count = 5;
    int cnt = 0;

    // 接口调用: 获取当前的运动指令 ID
    int exec_id = impl->getMotionControl()->getExecId();

    // 等待机械臂开始运动
    while (exec_id == -1) {
        if (cnt++ > max_retry_count) {
            return -1;
        }
        std::this_thread::sleep_for(std::chrono::milliseconds(50));
        exec_id = impl->getMotionControl()->getExecId();
    }

    // 等待机械臂动作完成
    while (impl->getMotionControl()->getExecId() != -1) {
        std::this_thread::sleep_for(std::chrono::milliseconds(50));
    }

    return 0;
}

int test02(RpcClientPtr rpc_cli)
{
    /*
     * 场景说明：
     *
     * 本示例用于标定“固定外部工具”场景。
     *
     * 典型应用：
     *   - 焊枪固定在工作站上；
     *   - 机器人末端夹持工件；
     *   - 机器人带着工件去接近固定焊枪完成焊接。
     *
     * 坐标系关系：
     *
     *   Base / World
     *      |
     *      |-- Remote Tool Frame
     *      |     固定焊枪坐标系，即外部工具坐标系
     *      |
     *      |-- Robot
     *            |
     *            |-- Flange
     *                  |
     *                  |-- TCP / Workpiece Frame
     *                        机器人夹持工件时，工件坐标系可临时定义在 TCP 上
     *
     * 本流程主要完成两件事：
     *
     *   1. 通过三点法标定固定焊枪坐标系在 Base 下的位姿：
     *
     *        F_base_remote_tool
     *
     *      该结果写入：
     *
     *        WObjectData::user_coord
     *
     *   2. 设置机器人夹持工件时，工件坐标系相对于法兰的位姿：
     *
     *        F_flange_workpiece
     *
     *      本示例中假设：
     *
     *        工件坐标系 = 当前 TCP 坐标系
     *
     *      因此直接使用当前 TCP offset：
     *
     *        WObjectData::obj_coord = getTcpOffset()
     *
     *      如果实际工件坐标系不在 TCP 上，则需要单独标定工件坐标系
     *      相对于法兰的位姿，不能直接使用 TCP offset。
     */

    // 1. 获取机器人接口
    auto robot_name = rpc_cli->getRobotNames().front();
    auto robot_interface = rpc_cli->getRobotInterface(robot_name);

    auto robot_config = robot_interface->getRobotConfig();
    auto robot_state = robot_interface->getRobotState();
    auto mc = robot_interface->getMotionControl();
    auto robot_algorithm = robot_interface->getRobotAlgorithm();

    // 2. 设置机械臂整体速度比例，避免标定运动过快
    robot_interface->getMotionControl()->setSpeedFraction(0.3);

    /*
     * 3. 设置当前机器人 TCP
     *
     * 注意：
     *   后续采集 tcp0 / tcp1 / tcp2 时，使用的是 getTcpPose()。
     *   因此 TCP offset 必须提前设置正确。
     *
     * 如果 TCP 不准确，则三点标定出来的固定焊枪坐标系也会整体偏移。
     *
     * 当前示例中 TCP 相对于法兰为：
     *
     *   x  = 0
     *   y  = 0
     *   z  = 0.0118 m
     *   rx = 0
     *   ry = 0
     *   rz = 0
     */
    robot_config->setTcpOffset({ 0, 0, 0.0118, 0, 0, 0 });

    /*
     * 4. 选择远端特征坐标系标定方法
     *
     * method = 0 表示 O_X_XY。
     *
     * O_X_XY 的三点含义：
     *
     *   点 0：远端坐标系原点 O
     *   点 1：远端坐标系 X 正方向上的一点
     *   点 2：远端坐标系 XY 平面第一象限内的一点
     *
     * 在固定焊枪场景下，可以这样定义：
     *
     *   点 0：焊枪 TCP / 焊枪尖端
     *   点 1：焊枪坐标系 X 正方向上的一点
     *   点 2：焊枪坐标系 XY 平面内的一点
     *
     * 最终算法会根据这三个点计算：
     *
     *   F_base_remote_tool
     *
     * 即：
     *
     *   固定焊枪坐标系在 Base 下的位姿。
     */
    constexpr int method = 0; // CoordCalibMethod::O_X_XY

    /*
     * 5. 采集点 0：远端坐标系原点
     *
     * 操作要求：
     *   机器人移动到第一个示教点；
     *   当前 TCP 对准固定焊枪坐标系原点；
     *   例如焊枪尖端。
     *
     * 记录：
     *   tcp0 = F_base_tcp_at_remote_origin
     */
    std::vector<double> q0{ -0.079587, -0.760964, 1.258906,
                            0.579449,  1.572367,  -0.01693 };

    mc->moveJoint(q0, 0.3, 0.3, 0, 0);
    waitArrival(robot_interface);
    auto tcp0 = robot_state->getTcpPose();

    /*
     * 6. 采集点 1：远端坐标系 X 正方向点
     *
     * 操作要求：
     *   机器人移动到第二个示教点；
     *   当前 TCP 位于固定焊枪坐标系 X 正方向上的某一点；
     *   距离原点尽量远一些，例如 100 mm ~ 200 mm；
     *   点 1 不要离点 0 太近，否则方向误差会被放大。
     *
     * 记录：
     *   tcp1 = F_base_tcp_at_remote_x_positive_point
     *
     * 注意：
     *   这里 q1 是提前示教好的关节位置。
     *   它必须对应远端坐标系 X 正方向上的点，
     *   不能只是随便移动到一个位置。
     */
    std::vector<double> q1{ -0.13508848, -0.90303335, 1.01002204,
                            0.58119464,  1.52524323,  -0.01692969 };

    mc->moveJoint(q1, 0.3, 0.3, 0, 0);
    waitArrival(robot_interface);
    auto tcp1 = robot_state->getTcpPose();

    /*
     * 7. 采集点 2：远端坐标系 XY 平面第一象限内的点
     *
     * 操作要求：
     *   机器人移动到第三个示教点；
     *   当前 TCP 位于远端坐标系 XY 平面内；
     *   且最好在第一象限，即 X > 0, Y > 0；
     *   该点用于确定远端坐标系的平面方向。
     *
     * 记录：
     *   tcp2 = F_base_tcp_at_remote_xy_plane_point
     *
     * 注意：
     *   tcp0、tcp1、tcp2 三点不能共线。
     *   如果三点接近共线，标定出的坐标系姿态会非常不稳定。
     */
    std::vector<double> q2{ 0.0089011792, -0.9028588221, 1.0138617625,
                            0.5794493117, 1.5723671231,  -0.0169296937 };

    mc->moveJoint(q2, 0.3, 0.3, 0, 0);
    waitArrival(robot_interface);
    auto tcp2 = robot_state->getTcpPose();

    /*
     * 8. 组织三点位姿
     *
     * 输入顺序必须和标定方法一致。
     *
     * 对于 O_X_XY：
     *
     *   pose[0] = 原点 O
     *   pose[1] = X 正方向点
     *   pose[2] = XY 平面内点
     *
     * 注意：
     *   这里传入的是 TCP 在 Base 下的位姿。
     *   算法通常主要使用其中的位置分量 xyz。
     */
    std::vector<std::vector<double>> pose;
    pose.reserve(3);
    pose.emplace_back(tcp0);
    pose.emplace_back(tcp1);
    pose.emplace_back(tcp2);

    /*
     * 9. 标定远端特征坐标系
     *
     * 返回值：
     *
     *   std::get<0>(ret) : 标定得到的远端特征坐标系位姿
     *   std::get<1>(ret) : 错误码，< 0 表示失败
     *
     * 对于当前固定焊枪场景：
     *
     *   coord = F_base_remote_tool
     *
     * 即：
     *
     *   固定焊枪坐标系在 Base 坐标系下的位姿描述。
     */
    auto ret = robot_algorithm->calibRemoteFeatureFrame(pose, method);

    if (std::get<1>(ret) < 0) {
        std::cout << "calibRemoteFeatureFrame failed, ret: " << std::get<1>(ret)
                  << std::endl;
        return -1;
    }

    auto coord = std::get<0>(ret); // 远端特征坐标系在 Base 坐标系下的位姿
    printPose(coord);

    /*
     * 10. 配置 WObjectData
     *
     * remote_tool = true：
     *
     *   表示当前是外部工具场景。
     *
     *   即：
     *     工具固定在工作站上；
     *     机器人末端夹持工件运动。
     *
     * user_coord：
     *
     *   在 remote_tool = true 时，这里填写固定外部工具坐标系
     *   在 Base / World 下的位姿。
     *
     *   当前场景中：
     *
     *     user_coord = 固定焊枪坐标系在 Base 下的位姿
     *
     * obj_coord：
     *
     *   表示工件坐标系相对于机器人末端挂载坐标系的位姿。
     *
     *   当前 demo 中简化处理：
     *
     *     工件坐标系原点 = TCP 原点
     *     工件坐标系姿态 = TCP 姿态
     *
     *   所以：
     *
     *     obj_coord = getTcpOffset()
     *
     *   也就是：
     *
     *     F_flange_workpiece = F_flange_tcp
     *
     *   如果实际工件坐标系不等于 TCP，
     *   例如工件坐标系定义在工件角点、孔中心、焊缝起点等位置，
     *   则必须单独标定或测量：
     *
     *     F_flange_workpiece
     *
     *   然后填入 obj_coord，而不能直接使用 getTcpOffset()。
     */
    WObjectData data;
    data.remote_tool = true;
    data.user_coord = coord;

    data.obj_coord = robot_config->getTcpOffset();

    /*
     * 11. 写入当前工件对象数据
     *
     * 设置完成后，控制器在后续轨迹规划时，可以理解为：
     *
     *   - 外部工具坐标系：固定焊枪坐标系；
     *   - 机器人携带的对象：工件坐标系；
     *   - 运动目标可以基于该 WorkObject 进行坐标转换。
     */
    robot_config->setWorkObjectData(data);

    return 0;
}

int main(int argc, char **argv)
{
#ifdef WIN32
    // 将Windows控制台输出代码页设置为 UTF-8
    SetConsoleOutputCP(CP_UTF8);
#endif

    auto rpc_cli = std::make_shared<RpcClient>();
    auto rtde_cli = std::make_shared<RtdeClient>();
    // 接口调用: 设置 RPC 超时
    rpc_cli->setRequestTimeout(1000);
    // 接口调用: 连接到 RPC 服务
    rpc_cli->connect("172.17.41.81", 30004);
    // 接口调用: 登录
    rpc_cli->login("aubo", "123456");

    // test01(rpc_cli, rtde_cli);
    test02(rpc_cli);

    // 接口调用: 退出登录
    rpc_cli->logout();
    // 接口调用: 断开连接
    rpc_cli->disconnect();
    return 0;
}
