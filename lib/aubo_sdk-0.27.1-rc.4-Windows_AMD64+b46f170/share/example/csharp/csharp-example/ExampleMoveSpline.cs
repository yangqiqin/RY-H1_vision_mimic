using System;
using System.Runtime.InteropServices;
using System.Threading;

namespace csharp_example
{
    class ExampleMoveSpline
    {
        const int RSERR_SUCC = 0;
        const string robot_ip = "192.168.15.139";
        const int server_port = 30004;
        const double M_PI = 3.14159265358979323846;
        const int max_start_retry_count = 200;

        static int waitMotionFinished(IntPtr motion_control, string motion_name)
        {
            int retry_count = 0;
            while (cSharpBinging_MotionControl.getExecId(motion_control) == -1)
            {
                if (retry_count++ >= max_start_retry_count)
                {
                    Console.Error.WriteLine("等待{0}开始超时", motion_name);
                    return -1;
                }
                Thread.Sleep(50);
            }

            Console.WriteLine("{0}开始", motion_name);
            while (cSharpBinging_MotionControl.getExecId(motion_control) != -1)
            {
                Thread.Sleep(50);
            }
            Console.WriteLine("{0}结束", motion_name);
            return RSERR_SUCC;
        }

        static int exampleMoveSpline(IntPtr cli)
        {
            double degree = M_PI / 180;
            double[][] joint_angles =
            {
                new double[] { 0, -15 * degree, 100 * degree, 25 * degree, 90 * degree, 0 },
                new double[] { 19.25 * degree, -6.08 * degree, 78.87 * degree, -5.05 * degree, 90 * degree, 19.25 * degree },
                new double[] { 28.20 * degree, -12.87 * degree, 52.22 * degree, -24.91 * degree, 90 * degree, 28.20 * degree },
                new double[] { 38.20 * degree, -15.58 * degree, 58.16 * degree, -16.25 * degree, 90 * degree, 38.20 * degree },
                new double[] { 38.20 * degree, -15.73 * degree, 91.05 * degree, 16.79 * degree, 90 * degree, 38.20 * degree }
            };
            double[] velocities = { 60 * degree, 60 * degree, 60 * degree, 180 * degree, 60 * degree };

            IntPtr[] robot_names = new IntPtr[10];
            string robot_name;
            try
            {
                for (int i = 0; i < robot_names.Length; ++i)
                {
                    robot_names[i] = Marshal.AllocHGlobal(100);
                }

                int robot_count = cSharpBinding_RPC.rpc_getRobotNames(cli, robot_names);
                if (robot_count <= 0)
                {
                    Console.Error.WriteLine("获取机器人名称失败");
                    return -1;
                }
                robot_name = Marshal.PtrToStringAnsi(robot_names[0]);
            }
            finally
            {
                for (int i = 0; i < robot_names.Length; ++i)
                {
                    if (robot_names[i] != IntPtr.Zero)
                    {
                        Marshal.FreeHGlobal(robot_names[i]);
                    }
                }
            }

            if (string.IsNullOrEmpty(robot_name))
            {
                Console.Error.WriteLine("机器人名称为空");
                return -1;
            }

            IntPtr robot_interface = cSharpBinding_RPC.rpc_getRobotInterface(cli, robot_name);
            if (robot_interface == IntPtr.Zero)
            {
                Console.Error.WriteLine("获取机器人接口失败");
                return -1;
            }

            IntPtr motion_control = cSharpBinging_RobotInterface.robot_getMotionControl(robot_interface);
            if (motion_control == IntPtr.Zero)
            {
                Console.Error.WriteLine("获取运动控制接口失败");
                return -1;
            }

            int ret = cSharpBinging_MotionControl.setSpeedFraction(motion_control, 0.8);
            if (ret != RSERR_SUCC)
            {
                Console.Error.WriteLine("设置速度比例失败，返回码: {0}", ret);
                return ret;
            }

            double acceleration = 80 * degree;
            ret = cSharpBinging_MotionControl.moveJoint(
                motion_control, joint_angles[0], acceleration, 60 * degree, 0, 0);
            if (ret != RSERR_SUCC)
            {
                Console.Error.WriteLine("运动到第一个路点失败，返回码: {0}", ret);
                return ret;
            }

            ret = waitMotionFinished(motion_control, "关节运动到第一个路点");
            if (ret != RSERR_SUCC)
            {
                return ret;
            }

            for (int i = 1; i < joint_angles.Length; ++i)
            {
                ret = cSharpBinging_MotionControl.moveSpline(
                    motion_control, joint_angles[i], acceleration, velocities[i], 0);
                if (ret != RSERR_SUCC)
                {
                    Console.Error.WriteLine("添加第 {0} 个路点失败，返回码: {1}", i + 1, ret);
                    return ret;
                }
                Console.WriteLine("已添加第 {0} 个路点", i + 1);
            }

            ret = cSharpBinging_MotionControl.moveSpline(
                motion_control, null, acceleration, 60 * degree, 0.005);
            if (ret != RSERR_SUCC)
            {
                Console.Error.WriteLine("结束路点添加失败，返回码: {0}", ret);
                return ret;
            }

            return waitMotionFinished(motion_control, "样条运动");
        }

        static void Main_MoveSpline(string[] args)
        {
            IntPtr rpc_client = cSharpBinding_RPC.rpc_create_client(0);
            if (rpc_client == IntPtr.Zero)
            {
                Console.Error.WriteLine("创建 RPC 客户端失败");
                return;
            }

            bool connected = false;
            bool logged_in = false;
            try
            {
                int ret = cSharpBinding_RPC.rpc_setRequestTimeout(rpc_client, 1000);
                if (ret != RSERR_SUCC)
                {
                    Console.Error.WriteLine("设置 RPC 超时失败，返回码: {0}", ret);
                    return;
                }

                ret = cSharpBinding_RPC.rpc_connect(rpc_client, robot_ip, server_port);
                if (ret != RSERR_SUCC)
                {
                    Console.Error.WriteLine("连接 RPC 服务失败，返回码: {0}", ret);
                    return;
                }
                connected = true;

                ret = cSharpBinding_RPC.rpc_login(rpc_client, "aubo", "123456");
                if (ret != RSERR_SUCC)
                {
                    Console.Error.WriteLine("登录失败，返回码: {0}", ret);
                    return;
                }
                logged_in = true;

                ret = exampleMoveSpline(rpc_client);
                if (ret != RSERR_SUCC)
                {
                    Console.Error.WriteLine("样条运动示例失败，返回码: {0}", ret);
                }
            }
            finally
            {
                if (logged_in)
                {
                    cSharpBinding_RPC.rpc_logout(rpc_client);
                }
                if (connected)
                {
                    cSharpBinding_RPC.rpc_disconnect(rpc_client);
                }
                cSharpBinding_RPC.rpc_destroy_client(rpc_client);
            }
        }
    }
}
