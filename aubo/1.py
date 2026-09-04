import pyaubo_sdk

client = pyaubo_sdk.RpcClient()
client.connect("192.168.1.100", 30004)
client.login("aubo", "123456")
robot_name = client.getRobotNames()[0]
ri = client.getRobotInterface(robot_name)
ra = ri.getRobotAlgorithm()

# 打印所有可用的方法
print(dir(ra))
# 或者尝试调用 addCollisionBox 看是否报错
# print(ra.addCollisionBox)  # 如果不存在会报 AttributeError