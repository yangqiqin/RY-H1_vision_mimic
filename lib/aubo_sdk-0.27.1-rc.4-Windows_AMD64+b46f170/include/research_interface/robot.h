#ifndef ARCS_RESEARCH_INTERFACE_ROBOT_H
#define ARCS_RESEARCH_INTERFACE_ROBOT_H

#include <functional>
#include <atomic>
#include <aubo/global_config.h>
#include <research_interface/rci_types.h>
#include <stdexcept>
#include "aubo_sdk/rpc.h"

namespace arcs {
namespace research_interface {

struct JointPositions
{
    JointPositions() {}
    JointPositions(const std::array<double, 7> &joint_positions)
        : q(joint_positions)
    {
    }
    JointPositions(std::initializer_list<double> joint_positions)
    {
        if (joint_positions.size() != q.size()) {
            throw std::invalid_argument(
                "Invalid number of elements in joint_positions.");
        }
        std::copy(joint_positions.begin(), joint_positions.end(), q.begin());
    }

    std::array<double, 7> q{};
    bool finished{ false };
};

struct JointSpeeds
{
    JointSpeeds() {}
    JointSpeeds(const std::array<double, 7> &joint_velocities)
        : qd(joint_velocities)
    {
    }
    JointSpeeds(std::initializer_list<double> joint_velocities)
    {
        if (joint_velocities.size() != qd.size()) {
            throw std::invalid_argument(
                "Invalid number of elements in joint_velocities.");
        }
        std::copy(joint_velocities.begin(), joint_velocities.end(), qd.begin());
    }

    std::array<double, 7> qd{};
    bool finished{ false };
};

struct JointCurrents
{
    JointCurrents() {}
    JointCurrents(const std::array<double, 7> &joint_currents)
        : current(joint_currents)
    {
    }
    JointCurrents(std::initializer_list<double> joint_currents)
    {
        if (joint_currents.size() != current.size()) {
            throw std::invalid_argument(
                "Invalid number of elements in joint_currents.");
        }
        std::copy(joint_currents.begin(), joint_currents.end(),
                  current.begin());
    }

    std::array<double, 7> current{};
    bool finished{ false };
};

class ARCS_ABI Robot
{
public:
    Robot(const std::string &ip, int port = 30030);
    ~Robot();

    // 启动机器人
    int startup();

    int setControlPeriod(int period = 5000);

    int movej(const JointPositions &jnt_pos);

    // 位置控制
    void control(
        std::function<JointPositions(const RobotState &, double duration)>
            control_callback,
        bool limit_rate = false, double cutoff_frequency = 100,
        bool loop = false);

    // 速度控制
    void veloControl(
        std::function<JointSpeeds(const RobotState &, double duration)>
            control_callback,
        bool limit_rate = false, double cutoff_frequency = 100,
        bool loop = false);

    // 电流控制
    void currentControl(
        std::function<JointCurrents(const RobotState &, double duration)>
            control_callback,
        bool limit_rate = false, double cutoff_frequency = 100,
        bool loop = false);

    // 实时读取机器人的状态
    void read(std::function<bool(const RobotState &)> read_callback);

    // 开始轨迹记录
    int startRecord(std::string csv_file);

    // 停止轨迹记录
    int stopRecord();

    // 设置控制模式
    int setServoMode(int mode);

protected:
    void *d_{ nullptr };
    bool init_{ false };
    int servo_mode_{ 1 };
    int period_{ 5000 };
};

} // namespace research_interface
} // namespace arcs

#endif
