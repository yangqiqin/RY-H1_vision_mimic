cmake_minimum_required(VERSION 3.10)
project(CollisionBoxServer)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# 设置输出目录
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/../bin)

# 如果有遨博 SDK，取消注释下面的配置
# set(AUBO_SDK_PATH "C:/aubo_sdk")
# include_directories(${AUBO_SDK_PATH}/include)
# link_directories(${AUBO_SDK_PATH}/lib)

add_executable(collision_box_server collision_box_server.cpp)

# 如果有遨博 SDK，取消注释下面的链接
# target_link_libraries(collision_box_server
#     arcs_common_interface
#     arcs_common
#     ws2_32
# )

# 如果没有 SDK，只链接 Windows Socket 库
if(WIN32)
    target_link_libraries(collision_box_server ws2_32)
endif()