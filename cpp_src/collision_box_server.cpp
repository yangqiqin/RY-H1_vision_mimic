// collision_box_server.cpp —— 遨博碰撞盒 Socket 服务端
//
// 用途：Python(pyaubo-sdk) 的 RobotAlgorithm 无法调用 addCollisionBox（固件/绑定层
// 报 32601 method not found），因此碰撞盒改由 C++ 直接调用遨博 C++ SDK。
// Python GUI → (TCP JSON) → 本服务 → 遨博 C++ SDK(真实机械臂 RPC)。
//
// 协议（JSON 行，单请求单响应，UTF-8）：
//   {command:"ping"}                        -> {"status":"pong"}
//   {command:"add", name, link, sizes:[l,w,h], poses:[x,y,z,rx,ry,rz]}
//                                           -> {"status":"ok","ret":0,"mode":"sdk"|"mock"}
//   {command:"remove", name}                -> {"status":"ok","ret":0,"mode":...}
//
// 两种构建模式：
//   1) 演示模式（无 SDK 也能编译，返回 mode=mock，GUI 会提示"未真正启用硬件保护"）：
//        g++ -O2 -std=c++17 collision_box_server.cpp -o bin/collision_box_server.exe -lws2_32
//   2) 真实模式（链接遨博 C++ SDK，返回 mode=sdk）：
//        -DUSE_REAL_AUBO_SDK 并链接 SDK（见文件尾部注释 / scripts/build_collision_server_msvc.bat）
//
// 命令行：collision_box_server.exe [port] [-r robot_ip]

#include <vector>
#include <memory>
#include <iostream>
#include <string>
#include <cstring>
#include <thread>
#include <chrono>
#include <sstream>
#include <cstdlib>

#ifdef _WIN32
#include <winsock2.h>
#include <ws2tcpip.h>
#pragma comment(lib, "ws2_32.lib")
#else
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <unistd.h>
#define SOCKET int
#define INVALID_SOCKET -1
#define SOCKET_ERROR -1
#define closesocket close
#endif

// ==================== 遨博 C++ SDK（真实模式） ====================
#ifdef USE_REAL_AUBO_SDK
#include "aubo_sdk/rpc.h"          // 需在编译时用 -I <sdk>/include 指向本机 SDK
using namespace arcs::common_interface;
using namespace arcs::aubo_sdk;
using CollisionApi   = RobotAlgorithm;                     // 真实算法接口
using RpcClientT     = RpcClient;                          // 真实 RPC 客户端
using RobotInterface = arcs::common_interface::RobotInterface;
static const char* kMode = "sdk";
#else
// ==================== 演示模式（mock，不链接 SDK） ====================
static const char* kMode = "mock";
// 占位类型：真实模式下不编译
class MockAlgorithm {
public:
    int addCollisionBox(const std::string& name, const std::string& link,
                        const std::vector<std::vector<double>>& sizes,
                        const std::vector<std::vector<double>>& poses) {
        std::cout << "[mock] addCollisionBox(" << name << "," << link << ")\n";
        for (auto& s : sizes) { for (double v : s) std::cout << v << " "; }
        std::cout << " | ";
        for (auto& p : poses) { for (double v : p) std::cout << v << " "; }
        std::cout << std::endl;
        return 0;
    }
    int removeCollisionObject(const std::string& name) {
        std::cout << "[mock] removeCollisionObject(" << name << ")\n";
        return 0;
    }
};
using CollisionApi = MockAlgorithm;
#endif

// 简化 JSON 读取（只读必要字段，不做完整 JSON 库依赖；容忍 "key": 后的空格）
namespace jsonmini {
// 定位 "key" 后冒号，返回其后第一个非空白字符的下标（找不到返回 npos）
size_t after_key(const std::string& s, const std::string& key) {
    std::string k = "\"" + key + "\"";
    size_t a = s.find(k);
    if (a == std::string::npos) return std::string::npos;
    size_t c = s.find(':', a + k.size());
    if (c == std::string::npos) return std::string::npos;
    size_t p = c + 1;
    while (p < s.size() && (s[p] == ' ' || s[p] == '\t')) p++;
    return p;
}
std::string getString(const std::string& s, const std::string& key) {
    size_t p = after_key(s, key);
    if (p == std::string::npos || p >= s.size() || s[p] != '"') return "";
    size_t b = s.find('"', p + 1);
    if (b == std::string::npos) return "";
    return s.substr(p + 1, b - p - 1);
}
std::vector<double> getArray(const std::string& s, const std::string& key) {
    std::vector<double> out;
    size_t p = after_key(s, key);
    if (p == std::string::npos || p >= s.size() || s[p] != '[') return out;
    size_t b = s.find(']', p + 1);
    if (b == std::string::npos) return out;
    std::string body = s.substr(p + 1, b - p - 1);
    std::stringstream ss(body);
    std::string item;
    while (std::getline(ss, item, ',')) {
        size_t q = item.find_first_not_of(" \t");
        if (q != std::string::npos) item = item.substr(q);
        q = item.find_last_not_of(" \t");
        if (q != std::string::npos) item = item.substr(0, q + 1);
        if (!item.empty() && (isdigit(item[0]) || item[0] == '-' || item[0] == '.')) {
            try { out.push_back(std::stod(item)); } catch (...) {}
        }
    }
    return out;
}
}  // namespace jsonmini

// ==================== 碰撞盒服务 ====================
class CollisionBoxServer {
public:
    CollisionBoxServer(int port, const std::string& robot_ip)
        : m_port(port), m_robot_ip(robot_ip), m_server_fd(INVALID_SOCKET) {}

    ~CollisionBoxServer() { stop(); }

    bool start() {
#ifdef _WIN32
        WSADATA wsa;
        if (WSAStartup(MAKEWORD(2, 2), &wsa) != 0) {
            std::cerr << "[C++] WSAStartup failed\n"; return false;
        }
#endif
        m_server_fd = socket(AF_INET, SOCK_STREAM, 0);
        if (m_server_fd == INVALID_SOCKET) { std::cerr << "[C++] socket failed\n"; return false; }
        int opt = 1;
        setsockopt(m_server_fd, SOL_SOCKET, SO_REUSEADDR, (char*)&opt, sizeof(opt));
        sockaddr_in addr{};
        addr.sin_family = AF_INET;
        addr.sin_addr.s_addr = INADDR_ANY;
        addr.sin_port = htons((uint16_t)m_port);
        if (bind(m_server_fd, (sockaddr*)&addr, sizeof(addr)) == SOCKET_ERROR) {
            std::cerr << "[C++] bind " << m_port << " failed\n"; closesocket(m_server_fd);
            return false;
        }
        if (listen(m_server_fd, 8) == SOCKET_ERROR) {
            std::cerr << "[C++] listen failed\n"; closesocket(m_server_fd); return false;
        }
        std::cout << "[C++] socket server listening on port " << m_port << std::endl;

        connect_to_robot();   // 失败不阻塞服务：命令时再报错
        m_running = true;
        m_accept_thread = std::thread([this] { accept_loop(); });
        return true;
    }

    void stop() {
        m_running = false;
        if (m_accept_thread.joinable()) m_accept_thread.join();
        if (m_server_fd != INVALID_SOCKET) { closesocket(m_server_fd); m_server_fd = INVALID_SOCKET; }
#ifdef _WIN32
        WSACleanup();
#endif
        std::cout << "[C++] server stopped\n";
    }

private:
    // ---------------- 机械臂连接（真实 SDK 或 mock） ----------------
    void connect_to_robot() {
#ifdef USE_REAL_AUBO_SDK
        try {
            m_rpc = std::make_shared<RpcClientT>();
            if (!m_rpc->connect(m_robot_ip, 30004)) {
                std::cerr << "[C++] RPC connect failed " << m_robot_ip << "\n";
                return;
            }
            if (!m_rpc->login("aubo", "123456")) {
                std::cerr << "[C++] RPC login failed\n";
                return;
            }
            auto names = m_rpc->getRobotNames();
            if (names.empty()) { std::cerr << "[C++] getRobotNames empty\n"; return; }
            auto ri = m_rpc->getRobotInterface(names.front());
            m_algo = ri->getRobotAlgorithm();
            std::cout << "[C++] robot connected: " << m_robot_ip
                      << " name=" << names.front() << " (real SDK)\n";
        } catch (const std::exception& e) {
            std::cerr << "[C++] connect robot exception: " << e.what() << "\n";
        }
#else
        std::cout << "[C++] DEMO MODE: not linked to real aubo SDK (mode=mock)\n";
        m_algo = std::make_shared<CollisionApi>();
#endif
    }

    bool robot_ready() const {
#ifdef USE_REAL_AUBO_SDK
        return m_algo != nullptr && m_rpc != nullptr;
#else
        return m_algo != nullptr;
#endif
    }

    // ---------------- socket 循环 ----------------
    void accept_loop() {
        while (m_running) {
            sockaddr_in ca{};
#ifdef _WIN32
            int len = sizeof(ca);
#else
            socklen_t len = sizeof(ca);
#endif
            SOCKET fd = accept(m_server_fd, (sockaddr*)&ca, &len);
            if (fd == INVALID_SOCKET) {
                if (m_running) std::cerr << "[C++] accept failed\n";
                continue;
            }
            std::thread([this, fd] { handle_client(fd); }).detach();
        }
    }

    void send_all(SOCKET fd, const std::string& msg) {
        size_t sent = 0;
        while (sent < msg.size()) {
            int n = send(fd, msg.c_str() + sent, (int)(msg.size() - sent), 0);
            if (n <= 0) return;
            sent += (size_t)n;
        }
    }

    void handle_client(SOCKET fd) {
        std::string buf;
        char tmp[2048];
        // 读请求：SO_RCVTIMEO=300ms；收到首包后再空等 300ms 即视为完整（小 JSON 命令）
#ifdef _WIN32
        int tv_ms = 300;
        setsockopt(fd, SOL_SOCKET, SO_RCVTIMEO, (const char*)&tv_ms, sizeof(tv_ms));
#else
        timeval tv{0, 300000};
        setsockopt(fd, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));
#endif
        bool got = false;
        int miss = 0;
        while (miss < 4) {
            int n = (int)recv(fd, tmp, sizeof(tmp), 0);
            if (n > 0) {
                buf.append(tmp, (size_t)n);
                got = true;
                miss = 0;
            } else if (n == 0) {
                break;                       // 对端关闭
            } else {
                if (got) break;              // 已收到数据且 300ms 无新包 → 完整
                miss++;                      // 等首个请求包
            }
        }
        std::string resp;
        if (!buf.empty()) {
            resp = dispatch(buf);
            std::cout << "[C++] req: " << buf << "\n[C++] resp: " << resp << "\n";
        }
        if (resp.empty()) resp = "{\"status\":\"error\",\"msg\":\"empty request\"}";
        send_all(fd, resp);
        closesocket(fd);
    }

    std::string dispatch(const std::string& json) {
        std::string cmd = jsonmini::getString(json, "command");
        if (cmd == "ping") return "{\"status\":\"pong\"}";
        if (cmd == "add") return handle_add(json);
        if (cmd == "remove") return handle_remove(json);
        return "{\"status\":\"error\",\"msg\":\"unknown command\",\"mode\":\"" +
               std::string(kMode) + "\"}";
    }

    std::string handle_add(const std::string& json) {
        std::string name = jsonmini::getString(json, "name");
        std::string link = jsonmini::getString(json, "link");
        if (link.empty()) link = "end_effector";
        auto sizes = jsonmini::getArray(json, "sizes");
        auto poses = jsonmini::getArray(json, "poses");
        if (name.empty()) return err("name empty");
        if (sizes.size() < 3) return err("sizes need >=3");
        if (poses.size() < 6) return err("poses need >=6");
        if (!robot_ready()) {
#ifdef USE_REAL_AUBO_SDK
            return err("robot not connected");
#else
            return err("demo mode: real aubo SDK not linked");
#endif
        }
        try {
            std::vector<std::vector<double>> sm{ {sizes[0], sizes[1], sizes[2]} };
            std::vector<std::vector<double>> pm{ {poses[0], poses[1], poses[2],
                                                  poses[3], poses[4], poses[5]} };
            int ret = m_algo->addCollisionBox(name, link, sm, pm);
            if (ret == 0) {
                return "{\"status\":\"ok\",\"ret\":0,\"mode\":\"" + std::string(kMode) + "\"}";
            }
            return err("SDK ret=" + std::to_string(ret));
        } catch (const std::exception& e) {
            return err(std::string("exception: ") + e.what());
        }
    }

    std::string handle_remove(const std::string& json) {
        std::string name = jsonmini::getString(json, "name");
        if (name.empty()) return err("name empty");
        if (!robot_ready()) {
#ifdef USE_REAL_AUBO_SDK
            return err("robot not connected");
#else
            return err("demo mode: real aubo SDK not linked");
#endif
        }
        try {
            int ret = m_algo->removeCollisionObject(name);
            if (ret == 0) {
                return "{\"status\":\"ok\",\"ret\":0,\"mode\":\"" + std::string(kMode) + "\"}";
            }
            return err("SDK ret=" + std::to_string(ret));
        } catch (const std::exception& e) {
            return err(std::string("exception: ") + e.what());
        }
    }

    static std::string err(const std::string& msg) {
        return "{\"status\":\"error\",\"msg\":\"" + msg + "\",\"mode\":\"" +
               std::string(kMode) + "\"}";
    }

    int m_port;
    std::string m_robot_ip;
    SOCKET m_server_fd;
    std::thread m_accept_thread;
    bool m_running = false;
    std::shared_ptr<CollisionApi> m_algo;
#ifdef USE_REAL_AUBO_SDK
    std::shared_ptr<RpcClientT> m_rpc;
#endif
};

// ==================== 主函数 ====================
// 用法: collision_box_server.exe [port] [-r robot_ip]
int main(int argc, char* argv[]) {
    int port = 9999;
    std::string robot_ip = "192.168.1.100";
    for (int i = 1; i < argc; i++) {
        std::string a = argv[i];
        if (a == "-r" || a == "--robot") {
            if (i + 1 < argc) robot_ip = argv[++i];
        } else {
            try { port = std::stoi(a); } catch (...) {}
        }
    }
    std::cout << "[C++] collision box server mode=" << kMode
              << " port=" << port << " robot_ip=" << robot_ip << std::endl;
    CollisionBoxServer srv(port, robot_ip);
    if (!srv.start()) { std::cerr << "[C++] start failed\n"; return 1; }
    while (true) std::this_thread::sleep_for(std::chrono::seconds(1));
    return 0;
}

// ==================== 真实 SDK 编译指引 ====================
// (1) 微软 MSVC (Visual Studio Developer Command Prompt)：
//     set SDK=E:\...\lib\aubo_sdk-0.27.1-rc.4-Windows_AMD64+b46f170
//     cl /EHsc /O2 /DUSE_REAL_AUBO_SDK /I"%SDK%\include" collision_box_server.cpp ^
//        /link /LIBPATH:"%SDK%\lib" aubo_sdk.lib robot_proxy.lib ws2_32.lib ^
//        /OUT:bin\collision_box_server.exe
//     运行目录需能找到 aubo_sdk.dll、robot_proxy.dll（把 %SDK%\lib 或 bin 拷到 exe 旁或加入 PATH）。
// (2) MinGW 真实链接：先为 aubo_sdk.dll 生成导入库再编译：
//     gendef aubo_sdk.dll && dlltool -d aubo_sdk.def -l libaubo_sdk.dll.a
//     g++ -O2 -std=c++17 -DUSE_REAL_AUBO_SDK -I"<sdk>/include" collision_box_server.cpp ^
//         -L. -laubo_sdk -lws2_32 -o bin/collision_box_server.exe
// (3) 演示模式（无 SDK 编译验证协议）：见文件头第 1) 条。
