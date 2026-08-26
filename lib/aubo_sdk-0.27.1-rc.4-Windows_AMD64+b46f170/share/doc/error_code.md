---
layout: doc
title: "错误码"
---

# 错误码

最后更新时间: 2026-08-06

## 系统错误 (0 - 102)

<div style="overflow-x: auto; width: 100%;">
<table style="min-width: 1280px; width: 100%; table-layout: fixed; border-collapse: collapse; word-break: break-word;">
<thead>
<tr>
<th style="width: 72px; padding: 6px 8px; vertical-align: top;">错误码</th>
<th style="width: 180px; padding: 6px 8px; vertical-align: top;">名称</th>
<th style="padding: 6px 8px; vertical-align: top;">描述</th>
<th style="padding: 6px 8px; vertical-align: top;">描述(中文)</th>
<th style="padding: 6px 8px; vertical-align: top;">建议</th>
<th style="padding: 6px 8px; vertical-align: top;">报错软件判断逻辑</th>
<th style="padding: 6px 8px; vertical-align: top;">维修排查点</th>
</tr>
</thead>
<tbody>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">0</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">DEBUG</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Debug message {}</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">1</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">POPUP</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Popup title: {}, msg: {}, mode: {}</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">2</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">POPUP_DISMISS</code></td>
<td style="padding: 6px 8px; vertical-align: top;">{}</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">3</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">SYSTEM_HALT</code></td>
<td style="padding: 6px 8px; vertical-align: top;">{}</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">4</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">INV_ARGUMENTS</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Invalid arguments.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">5</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">USER_NOTIFY</code></td>
<td style="padding: 6px 8px; vertical-align: top;">{}</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">6</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">POPUP_DISMISS_BY_ID</code></td>
<td style="padding: 6px 8px; vertical-align: top;">{}</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">MODBUS_SIGNAL_CREATED</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Modbus signal {} created.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">11</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">MODBUS_SIGNAL_REMOVED</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Modbus signal {} removed.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">12</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">MODBUS_SIGNAL_VALUE_CHANGED</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Modbus signal {} value changed to {}</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">13</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">RUNTIME_CONTEXT</code></td>
<td style="padding: 6px 8px; vertical-align: top;">tid: {} lineno: {} index: {} comment: {}</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">14</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">INTERP_CONTEXT</code></td>
<td style="padding: 6px 8px; vertical-align: top;">tid: {} lineno: {} index: {} comment: {}</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">15</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">PROGRAM_LOADED</code></td>
<td style="padding: 6px 8px; vertical-align: top;">program loaded: {}</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">16</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">TASK_DELETED</code></td>
<td style="padding: 6px 8px; vertical-align: top;">tid: {}</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">was deleted</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">20</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">MODBUS_SLAVE_BIT</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Modbus slave address: {} value {}</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">21</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">MODBUS_SLAVE_REG</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Modbus slave address: {} value {}</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">PNIO_SLAVE_SLOT_VALUE</code></td>
<td style="padding: 6px 8px; vertical-align: top;">PNIO slot: {} subslot {} index {} value {}</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">31</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">PNIO_CONNECT_STATUS</code></td>
<td style="padding: 6px 8px; vertical-align: top;">PNIO connection status changed to {}</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">32</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">PNIO_DEVICE_NAME</code></td>
<td style="padding: 6px 8px; vertical-align: top;">PNIO device name changed to {}</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">33</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">PNIO_IP</code></td>
<td style="padding: 6px 8px; vertical-align: top;">PNIO ip {} mask {} gateway {}</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">40</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">ICM_SERVER_STATUS</code></td>
<td style="padding: 6px 8px; vertical-align: top;">ICM server status changed to {}</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">50</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EIP_SLAVE_VALUE</code></td>
<td style="padding: 6px 8px; vertical-align: top;">EIP slave: trans_type {} index {} value {}</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">51</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EIP_SLAVE_CONNECT_STATUS</code></td>
<td style="padding: 6px 8px; vertical-align: top;">EIP slave connection status changed to {}</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">100</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">LOG_PROGRAM_SUCCESS</code></td>
<td style="padding: 6px 8px; vertical-align: top;">[{}] Load program {} successful</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">101</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">LOG_PROGRAM_FAILED</code></td>
<td style="padding: 6px 8px; vertical-align: top;">[{}] Load program {} failed, file not found</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">102</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">LOG_PROGRAM_FAILED2</code></td>
<td style="padding: 6px 8px; vertical-align: top;">[{}] Load program {} failed, configuration file (.ins) does not match</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
</tbody>
</table>
</div>

## 关节错误 (10001 - 10044)

<div style="overflow-x: auto; width: 100%;">
<table style="min-width: 1280px; width: 100%; table-layout: fixed; border-collapse: collapse; word-break: break-word;">
<thead>
<tr>
<th style="width: 72px; padding: 6px 8px; vertical-align: top;">错误码</th>
<th style="width: 180px; padding: 6px 8px; vertical-align: top;">名称</th>
<th style="padding: 6px 8px; vertical-align: top;">描述</th>
<th style="padding: 6px 8px; vertical-align: top;">描述(中文)</th>
<th style="padding: 6px 8px; vertical-align: top;">建议</th>
<th style="padding: 6px 8px; vertical-align: top;">报错软件判断逻辑</th>
<th style="padding: 6px 8px; vertical-align: top;">维修排查点</th>
</tr>
</thead>
<tbody>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10001</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">JOINT_ERR_OVER_CURRENET</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: over current</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">(a) Check for short circuit. (b) Do a Complete rebooting sequence. (c) If this happens more than two times in a row, replace joint</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10002</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">JOINT_ERR_OVER_VOLTAGE</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: over voltage</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">(a) Do a Complete rebooting sequence. (b) Check 48 V Power supply, current distributer, energy eater and Control Board for issues</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10003</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">JOINT_ERR_LOW_VOLTAGE</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: low voltage</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">(a) Do a Complete rebooting sequence. (b) Check for short circuit in robot arm. (c) Check 48 V Power supply, current distributer, energy eater and Control Board for issues</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10004</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">JOINT_ERR_OVER_TEMP</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: over temperature</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">(a) Check robot’s environment and make sure the robot is operating within recommended limits. (b) Do a Complete rebooting sequence</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10005</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">JOINT_ERR_HALL</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: hall</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10006</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">JOINT_ERR_ENCODER</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: encoder</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Check encoder connections</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10007</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">JOINT_ERR_ABS_ENCODER</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: abs encoder</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10008</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">JOINT_ERR_Q_CURRENT</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: detect current</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10009</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">JOINT_ERR_ENC_POLL</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: encoder pollustion</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10010</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">JOINT_ERR_ENC_Z_SIGNAL</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: enocder z signal</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10011</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">JOINT_ERR_ENC_CAL</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: encoder calibrate</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10012</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">JOINT_ERR_IMU_SENS</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: IMU sensor</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10013</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">JOINT_ERR_TEMP_SENS</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: TEMP sensor</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10014</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">JOINT_ERR_CAN_BUS</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: CAN bus error</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10015</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">JOINT_ERR_SYS_CUR</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: system current error</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10016</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">JOINT_ERR_SYS_POS</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: system position error</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10017</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">JOINT_ERR_OVER_SP</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: over speed</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10018</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">JOINT_ERR_OVER_ACC</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: over accelerate</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10019</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">JOINT_ERR_TRACE</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: trace accuracy</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10020</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">JOINT_ERR_TAG_POS_OVER</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: target position out of range</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10021</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">JOINT_ERR_TAG_SP_OVER</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: target speed out of range</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10022</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">JOINT_ERR_COLLISION</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: collision</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10023</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">JOINT_ERR_COMMON</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: unkown error. Check communication with joint.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10024</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">JOINT_ERR_SWITCH_SERVO_MODE</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: switch servo mode timeout.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10025</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">JOINT_ERR_MOTOR_STUCK</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: motor stucked.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10026</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">JOINT_ERR_REDUCER_OVER_TEMP</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: reducer over temperature</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">(a) Check robot’s environment and make sure the robot is operating within recommended limits. (b) Do a Complete rebooting sequence</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10027</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">JOINT_ERR_REDUCER_NTC</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: reducer TEMP sensor failure</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">(a) Check robot’s environment and make sure the robot is operating within recommended limits. (b) Do a Complete rebooting sequence</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10028</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">JOINT_ERR_ABS_MULTITURN</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: absolute encoder multiturn error</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">(a) Check robot’s environment and make sure the robot is operating within recommended limits. (b) Do a Complete rebooting sequence</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10029</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">JOINT_ERR_ADC_ZERO_OFFSET</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: ADC zero offset failure</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">(a) Check robot’s environment and make sure the robot is operating within recommended limits. (b) Do a Complete rebooting sequence</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10030</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">JOINT_ERR_SHORT_CIRCUIT</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: short circuit</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">(a) Check robot’s environment and make sure the robot is operating within recommended limits. (b) Do a Complete rebooting sequence</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10031</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">JOINT_ERR_PHASE_LOST</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: motor phase lost</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">(a) Check robot’s environment and make sure the robot is operating within recommended limits. (b) Do a Complete rebooting sequence</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10032</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">JOINT_ERR_BRAKE</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: brake failure</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">(a) Check robot’s environment and make sure the robot is operating within recommended limits. (b) Do a Complete rebooting sequence</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10033</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">JOINT_ERR_FIRMWARE_UPDATE</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: firmware update failure</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">(a) Check robot’s environment and make sure the robot is operating within recommended limits. (b) Do a Complete rebooting sequence</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10034</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">JOINT_ERR_BATTERY_LOW</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: battery low</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">(a) Check robot’s environment and make sure the robot is operating within recommended limits. (b) Do a Complete rebooting sequence</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10035</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">JOINT_ERR_PHASE_ALIGN</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: phase align</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">(a) Check robot’s environment and make sure the robot is operating within recommended limits. (b) Do a Complete rebooting sequence</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10036</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">JOINT_ERR_CAN_HW_FAULT</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: CAN bus hw fault</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">(a) Check robot’s environment and make sure the robot is operating within recommended limits. (b) Do a Complete rebooting sequence</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10037</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">JOINT_ERR_POS_DISCONTINUOUS</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: target position discontinuous</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">(a) Check robot’s environment and make sure the robot is operating within recommended limits. (b) Do a Complete rebooting sequence</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10038</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">JOINT_ERR_POS_INIT</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: position initiallization failure</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">(a) Check robot’s environment and make sure the robot is operating within recommended limits. (b) Do a Complete rebooting sequence</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10039</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">JOINT_ERR_TORQUE_SENSOR</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: torqure sensor failure</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">(a) Check robot’s environment and make sure the robot is operating within recommended limits. (b) Do a Complete rebooting sequence</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10040</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">JOINT_ERR_OFFLINE</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: joint may be offline</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">(a) Check joint&#39;s hardware. (b) Check joint&#39;s id.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10041</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">JOINT_ERR_BOOTLOADER</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: The joint is in bootloader mode. Retry firmware update.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10042</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">JOINT_ERR_SLAVE_OFFLINE</code></td>
<td style="padding: 6px 8px; vertical-align: top;">slave joint{} error: slave joint may be offline</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">(a) Check slave joint&#39;s hardware. (b) Check slave joint&#39;s id.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10043</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">JOINT_ERR_SLAVE_BOOTLOADER</code></td>
<td style="padding: 6px 8px; vertical-align: top;">slave joint{} error: The slave joint is in bootloader mode. Retry firmware update.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10044</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">JOINT_ERR_ETHERCAT_BUS</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: ETHERCAT bus error</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
</tbody>
</table>
</div>

## 关节扩展错误 (10401 - 10800)

<div style="overflow-x: auto; width: 100%;">
<table style="min-width: 1280px; width: 100%; table-layout: fixed; border-collapse: collapse; word-break: break-word;">
<thead>
<tr>
<th style="width: 72px; padding: 6px 8px; vertical-align: top;">错误码</th>
<th style="width: 180px; padding: 6px 8px; vertical-align: top;">名称</th>
<th style="padding: 6px 8px; vertical-align: top;">描述</th>
<th style="padding: 6px 8px; vertical-align: top;">描述(中文)</th>
<th style="padding: 6px 8px; vertical-align: top;">建议</th>
<th style="padding: 6px 8px; vertical-align: top;">报错软件判断逻辑</th>
<th style="padding: 6px 8px; vertical-align: top;">维修排查点</th>
</tr>
</thead>
<tbody>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10401</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_SHORT_CIRCUIT</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: short circuit protection</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10402</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_SHORT_CURRENT</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: over current</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10403</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_PHASEA_CURRENT</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: phase A over current</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10404</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_PHASEB_CURRENT</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: phase B over current</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10405</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_PHASEC_CURRENT</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: phase C over current</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10406</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_PHASE_CURRENT</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: phase over current</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10407</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_MOTOR_PHASE_LOSE</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: motor phase loss</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10408</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_BUS_OVER_VOLTAGE</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: bus over voltage</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10409</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_BUS_LOW_VOLTAGE</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: bus under voltage</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10410</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_OVERLOAD</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: overload</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10411</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_IPM_OVER_TEMP</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: IPM over temperature</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10412</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_REDUCER_OVER_TEMP</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: reducer over temperature</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10413</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_ADC_ZERO_OFFSET</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: ADC zero offset</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10414</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_REDUCER_NTC</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: reducer NTC fault</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10415</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_IPM_NTC</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: IPM NTC fault</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10416</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_TORQUE_SENSOR</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: torque sensor fault</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10417</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_TORQUE_SENSOR_COMM</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: torque sensor communication fault</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10418</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_MOTOR_ABS_ENC_COMM</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: motor-side absolute encoder communication fault</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10419</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_REDUCER_ABS_ENC_COMM</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: reducer-side absolute encoder communication fault</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10420</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_REDUCER_ABS_ENC_DATA</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: reducer-side absolute encoder data channel disabled warning</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10421</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_REDUCER_ABS_ENC_CMD</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: reducer-side absolute encoder command invalid warning</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10422</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_REDUCER_ABS_ENC_ERR</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: reducer-side absolute encoder fault</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10423</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_REDUCER_ABS_ENC_WARNING</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: reducer-side absolute encoder warning</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10424</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_BRAKE</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: brake fault</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10425</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_COMM_HWL</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: communication hardware layer error</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10426</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_FIRMWARE_UPDATE</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: firmware update failed</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10427</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_FLASH_OP</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: flash operation failed</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10428</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_MU_SAVE</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: multi-turn data error</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10429</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_DEMADATA_LOST</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: calibration zero point data lost</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10430</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_PARAMETER</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: parameter error</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10431</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_UVW_LOGIC</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: hall signal fault</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10432</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_UVW_ABZ</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: incremental encoder fault</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10433</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_ENC_Z_LOST</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: encoder Z signal lost</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10434</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_ENC_POLLUTE</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: encoder pollution</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10435</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_ENC_CALI</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: encoder calibration failed</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10436</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_MT_ABS_DATA</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: multi-turn absolute data error</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10437</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_ENC_TYPE_INFO</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: encoder type identified and saved</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10438</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_ENC_TYPE_ERROR</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: encoder type error</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10439</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_ENC_VERIFY</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: encoder verification failed</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10440</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_DUAL_ENC_ERROR</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: dual encoder deviation too large</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10441</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_DUAL_ENC_EANGLE</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: dual encoder electrical angle deviation too large</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10442</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_OBJECT_DICT_ERROR</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: object dictionary data error</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10443</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_MOTOR_STALL</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: motor stall protection</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10444</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_ABS_ENC_LOW_VOLT</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: absolute encoder low voltage</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10445</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_MT_BATTERY_LOW</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: multi-turn battery low voltage</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10446</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_POS_CMD</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: position command discontinuous</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10447</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_POS_OVER_LIMIT</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: position over limit</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10448</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_COMM_PROTO</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: communication protocol layer error</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10449</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_GRAVITY_PARA_WARNING</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: gravity compensation parameter invalid</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10450</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_GRAVITY_COMPENSATE_ERROR</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: gravity compensation value sudden change</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10451</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_LOW_RIGIDITY</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: collision soft float abnormal</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10452</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_POS_CMD_WARNING</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: position command unchanged during motion</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10453</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_SLAVE_COMM</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: master-slave MCU communication fault</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10454</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_POS_ERR</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: position following error too large</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10455</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_DUAL_POS_ERR</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: dual servo position sync error too large</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10456</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_DUAL_COMM_ERR</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: dual servo communication</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10457</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_CAN_BUSOFF</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: CAN bus-off warning</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10458</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_SYNC_SNAKE</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: sync frame jitter warning</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10459</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_SYNC_DISCON</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: sync frame discontinuous warning</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10460</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_RPDO_LOST</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: RPDO lost warning</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10461</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_RPDO_MANY</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: multiple RPDO in one sync cycle warning</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10462</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_GRAVITY_LOST</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: gravity compensation value lost</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10463</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_MAININT_TIME_WARN</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: servo main interrupt runtime warning</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10464</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_MAININT_TIME_ERROR</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: servo main interrupt runtime error</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10465</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_SPDINT_TIME_WARN</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: servo speed loop interrupt runtime warning</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10466</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_SPDINT_TIME_ERROR</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: servo speed loop interrupt runtime error</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10467</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_POS_CMD_JUMP_WARNING</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: position command sudden jump during motion</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10468</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_SYNC_TIMCOARSE</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: clock sync compensation status</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10469</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_ENC_Z_CNTS_ERR</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: incremental encoder Z signal or CNTS abnormal</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10470</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_SLAVE_OVER_CURRENT</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: slave MCU detected motor phase current over safe threshold</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10471</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_SLAVE_OVER_VOLTAGE</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: slave MCU detected DC bus voltage over upper threshold</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10472</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_SLAVE_UNDER_VOLTAGE</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: slave MCU detected DC bus voltage below lower threshold</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10473</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_SLAVE_POS_ERR</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: slave MCU detected master-slave motor position deviation out of range</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10474</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_SLAVE_SPEED_ERR</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: slave MCU detected master-slave motor speed deviation out of range</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10475</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_SLAVE_TRACE_ERR</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: slave MCU detected position following error out of control range</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10476</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_SLAVE_ABS_ERR</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: slave MCU detected absolute encoder feedback abnormal</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10477</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_SLAVE_ADC_ZERO_OFFSET</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: slave MCU detected current sampling zero offset out of calibration range</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10478</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_SLAVE_ENC_POLLUTE</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: slave MCU detected encoder signal quality degradation</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10479</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_SLAVE_ENC_Z_LOST</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: slave MCU detected encoder Z reference signal lost</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10480</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_SLAVE_COMM_OVER_TM</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: slave MCU detected master-slave communication timeout</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10481</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_SLAVE_TRQ_ERR</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: slave MCU detected master-slave motor torque deviation out of range</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10482</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_BRAKE_TYPE_ERR</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: brake type config mismatch with hardware</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10483</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_PHASE_ALIGN</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: phase alignment failed</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10484</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_POS_OVER_LIMIT_WARNING</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: position over limit</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10485</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_PHASE_ALIGN_WARNING</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: phase alignment warning</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10486</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_TASK_STACK_SHORTAGE</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: task stack insufficient</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10487</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_TASK_STACK_OVERFLOW</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: task stack overflow</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10488</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_SERVO_STEP</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} servo process step</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">For information only. No action required.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10489</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_MOTOR_ABS_ENC_ERR</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: motor-side absolute encoder fault</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10490</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_MU_SAVE_WARNING</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: multi-turn data warning</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10491</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_DATA_MIGRATE</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: data migration failed</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10492</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_ZERO_CALI_FAILED</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: zero calibration failed</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10493</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_TORQUE_STATIC_DIR_FAIL</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: torque static direction check failed</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10494</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_TORQUE_STATIC_VALUE_FAIL</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: torque static value check failed</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10495</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_TORQUE_DYNAMIC_DIR_FAIL</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: torque dynamic direction check failed</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10496</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_TORQUE_SENSOR_STUCK</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: torque sensor stuck</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10497</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_TORQUE_SENSOR_JUMP</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: torque sensor jump</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10498</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_TORQUE_CONFIG_INVALID</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: torque configuration invalid</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">10800</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_JOINT_EC_UNKNOWN</code></td>
<td style="padding: 6px 8px; vertical-align: top;">joint{} error: unknown error</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
</tbody>
</table>
</div>

## 扩展轴错误 (11001 - 11066)

<div style="overflow-x: auto; width: 100%;">
<table style="min-width: 1280px; width: 100%; table-layout: fixed; border-collapse: collapse; word-break: break-word;">
<thead>
<tr>
<th style="width: 72px; padding: 6px 8px; vertical-align: top;">错误码</th>
<th style="width: 180px; padding: 6px 8px; vertical-align: top;">名称</th>
<th style="padding: 6px 8px; vertical-align: top;">描述</th>
<th style="padding: 6px 8px; vertical-align: top;">描述(中文)</th>
<th style="padding: 6px 8px; vertical-align: top;">建议</th>
<th style="padding: 6px 8px; vertical-align: top;">报错软件判断逻辑</th>
<th style="padding: 6px 8px; vertical-align: top;">维修排查点</th>
</tr>
</thead>
<tbody>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">11001</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EXT_AXIS_ERR_COMMON</code></td>
<td style="padding: 6px 8px; vertical-align: top;">ext axis{} error: common</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Check communication with ext axis drive.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">11002</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EXT_AXIS_ERR_OVER_CURRENT</code></td>
<td style="padding: 6px 8px; vertical-align: top;">ext axis{} error: over current</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Check wiring/short circuit; reboot; if repeated replace drive/motor.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">11003</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EXT_AXIS_ERR_OVER_VOLTAGE</code></td>
<td style="padding: 6px 8px; vertical-align: top;">ext axis{} error: over voltage</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Check DC supply, regen, energy eater; reboot.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">11004</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EXT_AXIS_ERR_LOW_VOLTAGE</code></td>
<td style="padding: 6px 8px; vertical-align: top;">ext axis{} error: low voltage</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Check DC supply and cabling; reboot.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">11005</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EXT_AXIS_ERR_OVER_TEMP</code></td>
<td style="padding: 6px 8px; vertical-align: top;">ext axis{} error: over temperature</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Check environment/cooling; reboot.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">11006</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EXT_AXIS_ERR_HALL</code></td>
<td style="padding: 6px 8px; vertical-align: top;">ext axis{} error: hall fault</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Check hall sensor and motor cabling.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">11007</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EXT_AXIS_ERR_ENCODER</code></td>
<td style="padding: 6px 8px; vertical-align: top;">ext axis{} error: encoder fault</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Check encoder connection/cable/noise.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">11008</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EXT_AXIS_ERR_ABS_ENCODER</code></td>
<td style="padding: 6px 8px; vertical-align: top;">ext axis{} error: absolute encoder fault</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Check abs encoder power/cable; reboot.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">11009</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EXT_AXIS_ERR_CUR_CALIB</code></td>
<td style="padding: 6px 8px; vertical-align: top;">ext axis{} error: current calibration fault</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Reboot; check current sensing circuit.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">11010</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EXT_AXIS_ERR_Q_CURRENT</code></td>
<td style="padding: 6px 8px; vertical-align: top;">ext axis{} error: current detect fault</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Reboot; check current sensing circuit.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">11011</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EXT_AXIS_ERR_ENC_POLL</code></td>
<td style="padding: 6px 8px; vertical-align: top;">ext axis{} error: encoder pollution</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Check encoder contamination/noise; improve shielding.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">11012</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EXT_AXIS_ERR_ENC_Z_SIGNAL</code></td>
<td style="padding: 6px 8px; vertical-align: top;">ext axis{} error: encoder Z signal fault</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Check encoder Z channel and wiring.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">11013</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EXT_AXIS_ERR_ENC_CAL</code></td>
<td style="padding: 6px 8px; vertical-align: top;">ext axis{} error: encoder calibrate invalid</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Redo calibration; check encoder.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">11014</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EXT_AXIS_ERR_IMU</code></td>
<td style="padding: 6px 8px; vertical-align: top;">ext axis{} error: IMU fault</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Check IMU sensor and connection.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">11015</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EXT_AXIS_ERR_TEMP_SENSOR</code></td>
<td style="padding: 6px 8px; vertical-align: top;">ext axis{} error: temperature sensor fault</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Check temp sensor wiring; reboot.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">11016</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EXT_AXIS_ERR_ECAT_BUS</code></td>
<td style="padding: 6px 8px; vertical-align: top;">ext axis{} error: EtherCAT bus error</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Check EtherCAT cabling/topology/sync; reboot master/drive.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">11017</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EXT_AXIS_ERR_ECAT_CONFIG</code></td>
<td style="padding: 6px 8px; vertical-align: top;">ext axis{} error: EtherCAT config/ESI/SM/PDO fault</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Check ESI, Mailbox/SM/PDO mapping, vendor/product/revision match.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">11018</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EXT_AXIS_ERR_ECAT_SYNC</code></td>
<td style="padding: 6px 8px; vertical-align: top;">ext axis{} error: EtherCAT sync/frame/period fault</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Check DC sync, cycle time, frame loss; verify NIC/IRQ affinity.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">11019</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EXT_AXIS_ERR_SYS_CUR</code></td>
<td style="padding: 6px 8px; vertical-align: top;">ext axis{} error: system current fault</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Check current loop and load; reboot.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">11020</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EXT_AXIS_ERR_SYS_POS</code></td>
<td style="padding: 6px 8px; vertical-align: top;">ext axis{} error: position out of range</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Check encoder/scale/limits; reboot.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">11021</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EXT_AXIS_ERR_OVER_SPEED</code></td>
<td style="padding: 6px 8px; vertical-align: top;">ext axis{} error: over speed</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Check command limits and tuning parameters.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">11022</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EXT_AXIS_ERR_OVER_ACC</code></td>
<td style="padding: 6px 8px; vertical-align: top;">ext axis{} error: over acceleration</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Reduce acceleration/jerk; check tuning.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">11023</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EXT_AXIS_ERR_FOLLOW_ERROR</code></td>
<td style="padding: 6px 8px; vertical-align: top;">ext axis{} error: following error</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Check gains, load, saturation; verify feedback.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">11024</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EXT_AXIS_ERR_TAG_POS_OVER</code></td>
<td style="padding: 6px 8px; vertical-align: top;">ext axis{} error: target position out of range</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Check target limits and homing.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">11025</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EXT_AXIS_ERR_TAG_SPEED_OVER</code></td>
<td style="padding: 6px 8px; vertical-align: top;">ext axis{} error: target speed out of range</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Clamp speed; check profile settings.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">11026</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EXT_AXIS_ERR_TAG_CURRENT_OVER</code></td>
<td style="padding: 6px 8px; vertical-align: top;">ext axis{} error: target current out of range</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Clamp current/torque; check load.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">11027</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EXT_AXIS_ERR_COLLISION</code></td>
<td style="padding: 6px 8px; vertical-align: top;">ext axis{} error: collision</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Remove obstruction; check torque/force limits.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">11028</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EXT_AXIS_ERR_ADC_ZERO_OFFSET</code></td>
<td style="padding: 6px 8px; vertical-align: top;">ext axis{} error: ADC zero offset</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Reboot; check ADC/current sensor offset.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">11029</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EXT_AXIS_ERR_IPM_NTC</code></td>
<td style="padding: 6px 8px; vertical-align: top;">ext axis{} error: IPM NTC fault</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Check power module temperature sensing.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">11030</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EXT_AXIS_ERR_SHORT_CIRCUIT</code></td>
<td style="padding: 6px 8px; vertical-align: top;">ext axis{} error: short circuit</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Check motor phase wiring; insulation test.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">11031</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EXT_AXIS_ERR_MOTOR_STALL</code></td>
<td style="padding: 6px 8px; vertical-align: top;">ext axis{} error: motor stall</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Check mechanical jam/load; reduce accel; reboot.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">11032</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EXT_AXIS_ERR_ABS_MULTITURN</code></td>
<td style="padding: 6px 8px; vertical-align: top;">ext axis{} error: abs encoder multiturn fault</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Check abs encoder battery/params; reboot.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">11033</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EXT_AXIS_ERR_PHASE_LOST</code></td>
<td style="padding: 6px 8px; vertical-align: top;">ext axis{} error: motor phase lost</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Check phase wiring/connector; measure continuity.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">11034</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EXT_AXIS_ERR_BRAKE</code></td>
<td style="padding: 6px 8px; vertical-align: top;">ext axis{} error: brake fault</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Check brake wiring/power; verify brake release.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">11035</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EXT_AXIS_ERR_REDUCER_OVER_TEMP</code></td>
<td style="padding: 6px 8px; vertical-align: top;">ext axis{} error: reducer over temperature</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Check reducer temperature/cooling.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">11036</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EXT_AXIS_ERR_REDUCER_NTC</code></td>
<td style="padding: 6px 8px; vertical-align: top;">ext axis{} error: reducer NTC fault</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Check reducer temperature sensor.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">11037</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EXT_AXIS_ERR_FIRMWARE_UPDATE</code></td>
<td style="padding: 6px 8px; vertical-align: top;">ext axis{} error: firmware update fault</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Retry update; check power stability.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">11038</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EXT_AXIS_ERR_FLASH_OP</code></td>
<td style="padding: 6px 8px; vertical-align: top;">ext axis{} error: flash operation fault</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Retry; if persistent replace drive.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">11039</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EXT_AXIS_ERR_EXT_ABS_ENC</code></td>
<td style="padding: 6px 8px; vertical-align: top;">ext axis{} error: motor-side abs encoder comm fault</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Check external abs encoder link/power.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">11040</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EXT_AXIS_ERR_DRIVE_FAULT</code></td>
<td style="padding: 6px 8px; vertical-align: top;">ext axis{} error: drive fault</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Check drive alarm code; reboot; replace if repeated.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">11041</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EXT_AXIS_ERR_OVERLOAD</code></td>
<td style="padding: 6px 8px; vertical-align: top;">ext axis{} error: overload</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Reduce load; check mechanics and tuning.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">11042</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EXT_AXIS_ERR_HARDWARE_LIMIT</code></td>
<td style="padding: 6px 8px; vertical-align: top;">ext axis{} error: hardware limit triggered</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Move away from limit; check limit switch.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">11043</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EXT_AXIS_ERR_SERVO_MODE_TIMEOUT</code></td>
<td style="padding: 6px 8px; vertical-align: top;">ext axis{} error: switch servo mode timeout</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Check mode transition and comm; reboot.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">11044</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EXT_AXIS_ERR_UVW_ABZ</code></td>
<td style="padding: 6px 8px; vertical-align: top;">ext axis{} error: UVW/ABZ fault</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Check phase/encoder signals wiring.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">11045</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EXT_AXIS_ERR_BATTERY_LOW</code></td>
<td style="padding: 6px 8px; vertical-align: top;">ext axis{} error: battery low</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Replace encoder battery; reboot.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">11046</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EXT_AXIS_ERR_PHASE_ALIGN</code></td>
<td style="padding: 6px 8px; vertical-align: top;">ext axis{} error: phase align fail</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Redo phase alignment; check motor params.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">11047</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EXT_AXIS_ERR_POS_DISCONTINUOUS</code></td>
<td style="padding: 6px 8px; vertical-align: top;">ext axis{} error: position command discontinuous</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Check trajectory generation and limits.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">11048</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EXT_AXIS_ERR_POS_INIT</code></td>
<td style="padding: 6px 8px; vertical-align: top;">ext axis{} error: position initialization failure</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Check encoder init/homing procedure.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">11049</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EXT_AXIS_ERR_TORQUE_SENSOR</code></td>
<td style="padding: 6px 8px; vertical-align: top;">ext axis{} error: torque sensor fault</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Check torque sensor wiring/calibration.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">11050</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EXT_AXIS_ERR_ABS_ENC_LOW_VOLT</code></td>
<td style="padding: 6px 8px; vertical-align: top;">ext axis{} error: abs encoder low voltage</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Check encoder supply voltage and cable.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">11051</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EXT_AXIS_ERR_OFFLINE</code></td>
<td style="padding: 6px 8px; vertical-align: top;">ext axis{} error: ext axis offline</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Check hardware and axis id; check EtherCAT state.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">11052</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EXT_AXIS_ERR_BOOTLOADER</code></td>
<td style="padding: 6px 8px; vertical-align: top;">ext axis{} error: ext axis in bootloader</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Retry firmware update.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">11053</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EXT_AXIS_ERR_SLAVE_OFFLINE</code></td>
<td style="padding: 6px 8px; vertical-align: top;">ext axis slave{} error: slave offline</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Check slave hardware and id.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">11054</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EXT_AXIS_ERR_SLAVE_BOOTLOADER</code></td>
<td style="padding: 6px 8px; vertical-align: top;">ext axis slave{} error: slave in bootloader</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Retry firmware update.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">11055</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EXT_AXIS_ERR_EEPROM</code></td>
<td style="padding: 6px 8px; vertical-align: top;">ext axis{} error: EEPROM/param store fault</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Check EEPROM/parameter storage; power cycle.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">11056</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EXT_AXIS_ERR_PARAM_CONFIG</code></td>
<td style="padding: 6px 8px; vertical-align: top;">ext axis{} error: parameter/config fault</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Verify parameter set; restore defaults if needed.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">11057</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EXT_AXIS_ERR_STO</code></td>
<td style="padding: 6px 8px; vertical-align: top;">ext axis{} error: STO safety fault</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Check STO wiring/safety chain; reset safety.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">11058</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EXT_AXIS_ERR_ENCRYPT_CHIP</code></td>
<td style="padding: 6px 8px; vertical-align: top;">ext axis{} error: encrypt chip/key fault</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Check encryption chip/keys/firmware compatibility.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">11059</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EXT_AXIS_ERR_BRAKE_RES_OVERLOAD</code></td>
<td style="padding: 6px 8px; vertical-align: top;">ext axis{} error: brake resistor overload</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Check brake resistor/regen circuit; duty cycle.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">11060</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EXT_AXIS_ERR_POWER_LINE_OPEN</code></td>
<td style="padding: 6px 8px; vertical-align: top;">ext axis{} error: motor power line open</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Check motor power cable continuity/connector.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">11061</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EXT_AXIS_ERR_HOMING</code></td>
<td style="padding: 6px 8px; vertical-align: top;">ext axis{} error: homing fault</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Check homing sensor/origin procedure; retry.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">11062</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EXT_AXIS_ERR_TUNING_FAIL</code></td>
<td style="padding: 6px 8px; vertical-align: top;">ext axis{} error: tuning fail</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Redo tuning; reduce resonance; check mechanics.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">11063</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EXT_AXIS_ERR_INERTIA_ID_FAIL</code></td>
<td style="padding: 6px 8px; vertical-align: top;">ext axis{} error: inertia identification fail</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Check load; redo inertia ID; adjust conditions.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">11064</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EXT_AXIS_ERR_FLYAWAY</code></td>
<td style="padding: 6px 8px; vertical-align: top;">ext axis{} error: flyaway</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Emergency stop; check feedback polarity/scale; inspect drive params.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">11065</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EXT_AXIS_ERR_SPEED_PULSE_OVER</code></td>
<td style="padding: 6px 8px; vertical-align: top;">ext axis{} error: feedback pulse overspeed</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Check encoder feedback and scaling; reduce speed.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">11066</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EXT_AXIS_ERR_CTRL_LOOP</code></td>
<td style="padding: 6px 8px; vertical-align: top;">ext axis{} error: control loop/timeout fault</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Check sampling/current loop/comm timeout; reboot.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
</tbody>
</table>
</div>

## 安全接口板错误 (20001 - 20027)

<div style="overflow-x: auto; width: 100%;">
<table style="min-width: 1280px; width: 100%; table-layout: fixed; border-collapse: collapse; word-break: break-word;">
<thead>
<tr>
<th style="width: 72px; padding: 6px 8px; vertical-align: top;">错误码</th>
<th style="width: 180px; padding: 6px 8px; vertical-align: top;">名称</th>
<th style="padding: 6px 8px; vertical-align: top;">描述</th>
<th style="padding: 6px 8px; vertical-align: top;">描述(中文)</th>
<th style="padding: 6px 8px; vertical-align: top;">建议</th>
<th style="padding: 6px 8px; vertical-align: top;">报错软件判断逻辑</th>
<th style="padding: 6px 8px; vertical-align: top;">维修排查点</th>
</tr>
</thead>
<tbody>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">20001</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">IFB_ERR_ROBOTTYPE</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Robot error type!</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">20002</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">IFB_ERR_ADXL_SENS</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Base Acceleration sensor error!</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">20003</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">IFB_ERR_EN_LINE</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Encoder line error!</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">20004</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">IFB_ERR_ENTER_HDG_MODE</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Robot enter handguide mode!</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">20005</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">IFB_ERR_EXIT_HDG_MODE</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Robot exit handguide mode!</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">20006</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">IFB_ERR_MAC_DATA_BREAK</code></td>
<td style="padding: 6px 8px; vertical-align: top;">MAC data break!</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">20007</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">IFB_ERR_DRV_FIRMWARE_VERSION</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Motor driver firmware version error!</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">20008</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">INIT_ERR_EN_DRV</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Motor driver enable failed!</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">20009</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">INIT_ERR_EN_AUTO_BACK</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Motor driver enable auto back failed!</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">20010</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">INIT_ERR_EN_CUR_LOOP</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Motor driver enable current loop failed!</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">20011</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">INIT_ERR_SET_TAG_CUR</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Motor driver set target current failed!</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">20012</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">INIT_ERR_RELEASE_BRAKE</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Motor driver release brake failed!</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">20013</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">INIT_ERR_EN_POS_LOOP</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Motor driver enable postion loop failed!</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">20014</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">INIT_ERR_SET_MAX_ACC</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Motor set max accelerate failed!</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">20015</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">SAFETY_ERR_PROTECTION_STOP_TIMEOUT</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Protective stop timeout!</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">20016</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">SAFETY_ERR_REDUCED_MODE_TIMEOUT</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Reduced mode timeout!</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">20017</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">SYS_ERR_MCU_COM</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Robot system error: mcu communication error!</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">20018</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">SYS_ERR_RS485_COM</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Robot system error: RS485 communication error!</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">20019</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">IFB_ERR_DISCONNECTED</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Interface board may be disconnected. Please check connection between IPC and Interface board.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">20020</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">IFB_ERR_PAYLOAD_ERROR</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Payload error.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">20021</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">IFB_OFFLINE</code></td>
<td style="padding: 6px 8px; vertical-align: top;">ifaceboard error: ifaceboard may be offline</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">(a) Check ifaceboard&#39;s hardware. (b) Check ifaceboard&#39;s id.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">20022</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">IFB_ERR_BOOTLOADER</code></td>
<td style="padding: 6px 8px; vertical-align: top;">ifaceboard error: The ifaceboard is in bootloader mode. Retry firmware update.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">20023</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">IFB_SLAVE_OFFLINE</code></td>
<td style="padding: 6px 8px; vertical-align: top;">interface slave board error: interface slave board may be offline</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">(a) Check interface slave board&#39;s hardware. (b) Check interface slave board&#39;s id.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">20024</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">IFB_SLAVE_ERR_BOOTLOADER</code></td>
<td style="padding: 6px 8px; vertical-align: top;">interface slave board error: The interface slave board is in bootloader mode. Retry firmware update.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">20025</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">IFB_TOOL_ERR_ADXL_SENS</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Tool Acceleration sensor error!</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">20026</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">HANDLE_OFFLINE</code></td>
<td style="padding: 6px 8px; vertical-align: top;">handle error: handle may be offline</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">(a) Check handle&#39;s hardware. (b) Check handle&#39;s id.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">20027</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">HANDLE_ERR_BOOTLOADER</code></td>
<td style="padding: 6px 8px; vertical-align: top;">handle error: The handle is in bootloader mode. Retry firmware update.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
</tbody>
</table>
</div>

## 运行时错误 (30001 - 30450)

<div style="overflow-x: auto; width: 100%;">
<table style="min-width: 1280px; width: 100%; table-layout: fixed; border-collapse: collapse; word-break: break-word;">
<thead>
<tr>
<th style="width: 72px; padding: 6px 8px; vertical-align: top;">错误码</th>
<th style="width: 180px; padding: 6px 8px; vertical-align: top;">名称</th>
<th style="padding: 6px 8px; vertical-align: top;">描述</th>
<th style="padding: 6px 8px; vertical-align: top;">描述(中文)</th>
<th style="padding: 6px 8px; vertical-align: top;">建议</th>
<th style="padding: 6px 8px; vertical-align: top;">报错软件判断逻辑</th>
<th style="padding: 6px 8px; vertical-align: top;">维修排查点</th>
</tr>
</thead>
<tbody>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30001</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">ROBOT_BE_PULLING</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Something is pulling the robot.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Please check TCP configuration,payload and mounting settings</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30002</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">PSTOP_ELBOW_POS</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Protective Stop: Elbow position close to safety plane limits.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Please move robot Elbow joint away from the safety plane</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30003</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">PSTOP_STOP_TIME</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Protective Stop: Exceeding user safety settings for stopping time.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">(a) Check speeds and accelerations in the program (b) Check usage of TCP,payload and CoG correctly (c) Check external equipmentactivation if correctly set</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30004</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">PSTOP_STOP_DISTANCE</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Protective Stop: Exceeding user safety settings for stopping distance.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">(a) Check speeds and accelerations in the program (b) Check usage of TCP,payload and CoG correctly (c) Check external equipmentactivation if correctly set</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30005</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">PSTOP_CLAMP</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Protective Stop: Danger of clamping between the Robot’s lower arm and tool.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">(a) Check speeds and accelerations in the program (b) Check usage of TCP,payload and CoG correctly (c) Check external equipmentactivation if correctly set</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30006</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">PSTOP_POS_LIMIT</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Protective Stop: Position close to joint limits</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30007</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">PSTOP_ORI_LIMIT</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Protective Stop: Tool orientation close to limits</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30008</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">PSTOP_PLANE_LIMIT</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Protective Stop: Position close to safety plane limits</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30009</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">PSTOP_POS_DEVIATE</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Protective Stop: Position deviates from path</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Check payload, center of gravity and acceleration settings.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30010</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">JOINT_CHK_PAYLOAD</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Joint {}: Check payload, center of gravity and acceleration settings. Log screen may contain additional information.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30011</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">PSTOP_SINGULARITY</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Protective Stop: Position in singularity.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Please use MoveJ or change the motion</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30012</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">PSTOP_CANNOT_MAINTAIN</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Protective Stop: Robot cannot maintain its position, check if payload is correct</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30013</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">PSTOP_WRONG_PAYLOAD</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Protective Stop: Wrong payload or mounting detected, or something is pushing the robot when entering Freedrive mode</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Verify that the TCP configuration and mounting in the used installation is correct</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30014</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">PSTOP_JOINT_COLLISION</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Protective Stop: Collision detected by joint {}</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Make sure no objects are in the path of the robot and resume the program</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30015</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">PSTOP_POS_DISAGREE</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Protective stop: The robot was powered off last time due to a joint position disagreement.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">(a) Verify that the robot position in the 3D graphics matches the real robot, to ensure that the encoders function before releasing the brakes. Stand back and monitor the robot performing its first program cycle as expected. (b) If the position is not correct, the robot must be repaired. In this case, click Power Off Robot. (c) If the position is correct, please tick the check box below the 3D graphics and click Robot Position Verified</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30016</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">TARGET_JOINT_SPEED_EXCEED</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Target joint speed exceed limits</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30017</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">TARGET_POS_SUDDEN_CHG</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Sudden change in target position</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30018</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">SUDDEN_STOP</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Sudden stop.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">To abort a motion, use &quot;stopj&quot; or &quot;stopl&quot; script commands to generate a smooth deceleration before using &quot;wait&quot;. Avoid aborting motions between waypoints with blend”</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30019</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">ROBOT_STOP_ABNORMAL</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Robot has not stopped in the allowed reaction and braking time</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30020</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">PROG_INVALID_SETP</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Robot program resulted in invalid setpoint.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Please review waypoints in the program</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30021</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">BLEND_INVALID_SETP</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Blending failed and resulted in an invalid setpoint.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Try changing the blend radius or contact technical support</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30022</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">APPROACH_SINGULARITY</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Robot approaching singularity – Acceleration threshold failed.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Review waypoints in the program, try using MoveJ instead of MoveL in the position close to singularity</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30023</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">TSPEED_UNMATCH_POS</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Target speed does not match target position</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30024</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">INCONSIS_TPOS_SPD</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Inconsistency between target position and speed</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30025</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">JOINT_TSPD_UNMATCH_POS</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Target joint speed does not match target joint position change – Joint {}</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30026</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">FIELDBUS_INPUT_DISCONN</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Fieldbus input disconnected.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Please check fieldbus connections (RTDE, ModBus, EtherNet/IP and Profinet) or disable the fieldbus in the installation. Check RTDE watchdog feature. Check if a URCap is using this feature.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30027</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">OPMODE_CHANGED</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Operational mode changed: {}</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30028</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">NO_KIN_CALIB</code></td>
<td style="padding: 6px 8px; vertical-align: top;">No Kinematic Calibration found (calibration.conf file is either corrupt or missing).</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">A new kinematics calibration may be needed if the robot needs to improve its kinematics, otherwise, ignore this message)</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30029</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">KIN_CALIB_UNMATCH_JOINT</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Kinematic Calibration for the robot does not match the joint(s).</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">If moving a program from a different robot to this one, rekinematic calibrate the second robot to improve kinematics, otherwise ignore this message.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30030</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">KIN_CALIB_UNMATCH_ROBOT</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Kinematic Calibration does not match the robot.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Please check if the serial number of the robot arm matches the Control Box</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30031</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">JOINT_OFFSET_CHANGED</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Large movement of the robot detected while it was powered off. The joints were moved while it was powered off, or the encoders do not function</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30032</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">OFFSET_CHANGE_HIGH</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Change in offset is too high</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30033</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">JOINT_SPEED_LIMIT</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Close to joint speed safety limit.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Review program speed and acceleration</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30034</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">TOOL_SPEED_LIMIT</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Close to tool speed safety limit.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Review program speed and acceleration</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30035</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">MOMENTUM_LIMIT</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Close to momentum safety limit.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Review program speed and acceleration</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30036</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">ROBOT_MV_STOP</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Robot is moving when in Stop Mode</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30037</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">HAND_PROTECTION</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Hand protection: Tool is too close to the lower arm: {} meter.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">(a) Check wrist position. (b) Verify mounting (c) Do a Complete rebooting sequence (d) Update software (e) Contact your local AUBO Robots service provider for assistance</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30038</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">WRONG_SAFETYMODE</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Wrong safety mode: {}</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30039</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">SAFETYMODE_CHANGED</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Safety mode changed: {}</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30040</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">JOINT_ACC_LIMIT</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Close to joint acceleration safety limit</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30041</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">TOOL_ACC_LIMIT</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Close to tool acceleration safety limit</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30042</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">JOINT_TEMPERATURE_LIMIT</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Joint {} temperature too high(&gt;{}℃)</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30043</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">CONTROL_BOX_TEMPERATURE_LIMIT</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Control box temperature too high(&gt;{}℃)</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30044</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">ROBOT_EMERGENCY_STOP</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Robot emergency stop</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30045</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">ROBOTMODE_CHANGED</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Robot mode changed: {}</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30046</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">ROBOTMODE_ERROR</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Wrong robot mode: {}</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30047</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">POSE_OUT_OF_REACH</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Target pose [{}] out of reach</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30048</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">TP_PLAN_FAILED</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Trajectory plan FAILED.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30049</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">START_FORCE_FAILED</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Start force control failed, because force sensor does not exist.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30050</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">OVER_SAFE_PLANE_LIMIT</code></td>
<td style="padding: 6px 8px; vertical-align: top;">{} axis exceeds the safety plane limit (Move_type:{} id:{}).</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Please move the robot to the safety plane range.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30051</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">POWERON_FAIL_VIOLATION</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Failed to power on because the robot safety mode is in violation</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30052</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">POWERON_FAIL_SYSTEMEMERGENCYSTOP</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Failed to power on because the robot safety mode is in system emergency stop</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30053</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">POWERON_FAIL_ROBOTEMERGENCYSTOP</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Failed to power on because the robot safety mode is in robot emergency stop</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Pop up the red emergency stop button on the teach pendant when the robot is in a safe range of motion</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30054</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">POWERON_FAIL_FAULT</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Failed to power on because the robot safety mode is in fault</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30055</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">STARTUP_FAIL_VIOLATION</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Failed to startup because the robot safety mode is in violation</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30056</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">STARTUP_FAIL_SYSTEMEMERGENCYSTOP</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Failed to startup because the robot safety mode is in system emergency stop</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30057</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">STARTUP_FAIL_ROBOTEMERGENCYSTOP</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Failed to startup because the robot safety mode is in robot emergency stop</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Pop up the red emergency stop button on the teach pendant when the robot is in a safe range of motion</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30058</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">STARTUP_FAIL_FAULT</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Failed to startup because the robot safety mode is in fault</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30059</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">BACKDRIVE_FAIL_VIOLATION</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Failed to backdrive because the robot safety mode is in violation</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30060</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">BACKDRIVE_FAIL_SYSTEMEMERGENCYSTOP</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Failed to backdrive because the robot safety mode is in system emergency stop</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30061</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">BACKDRIVE_FAIL_ROBOTEMERGENCYSTOP</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Failed to backdrive because the robot safety mode is in robot emergency stop</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Pop up the red emergency stop button on the teach pendant when the robot is in a safe range of motion</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30062</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">BACKDRIVE_FAIL_FAULT</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Failed to backdrive because the robot safety mode is in fault</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30063</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">SETSIM_FAIL_VIOLATION</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Switch sim mode failed because the robot safety mode is in violation</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30064</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">SETSIM_FAIL_SYSTEMEMERGENCYSTOP</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Switch sim mode failed because the robot safety mode is in system emergency stop</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30065</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">SETSIM_FAIL_ROBOTEMERGENCYSTOP</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Switch sim mode failed because the robot safety mode is in robot emergency stop</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Pop up the red emergency stop button on the teach pendant when the robot is in a safe range of motion</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30066</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">SETSIM_FAIL_FAULT</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Switch sim mode failed because the robot safety mode is in fault</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30067</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">FREEDRIVE_FAIL_VIOLATION</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Enable handguide mode failed because the robot safety mode is in violation</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30068</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">FREEDRIVE_FAIL_SYSTEMEMERGENCYSTOP</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Enable handguide mode failed because the robot safety mode is in system emergency stop</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30069</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">FREEDRIVE_FAIL_ROBOTEMERGENCYSTOP</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Enable handguide mode failed because the robot safety mode is in robot emergency stop</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Pop up the red emergency stop button on the teach pendant when the robot is in a safe range of motion</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30070</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">FREEDRIVE_FAIL_FAULT</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Enable handguide mode failed because the robot safety mode is in fault</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30071</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">UPFIRMWARE_FAIL_VIOLATION</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Firmware update failed because the robot safety mode is in violation</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30072</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">UPFIRMWARE_FAIL_SYSTEMEMERGENCYSTOP</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Firmware update failed because the robot safety mode is in system emergency stop</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30073</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">UPFIRMWARE_FAIL_ROBOTEMERGENCYSTOP</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Firmware update failed because the robot safety mode is in robot emergency stop</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Pop up the red emergency stop button on the teach pendant when the robot is in a safe range of motion</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30074</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">UPFIRMWARE_FAIL_FAULT</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Firmware update failed because the robot safety mode is in fault</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30075</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">SETPERSOSTENT_FAIL_VIOLATION</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Set persistent parameter failed because the robot safety mode is in violation</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30076</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">SETPERSOSTENT_FAIL_SYSTEMEMERGENCYSTOP</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Set persistent parameter failed because the robot safety mode is in system emergency stop</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30077</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">SETPERSOSTENT_FAIL_ROBOTEMERGENCYSTOP</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Set persistent parameter failed because the robot safety mode is in robot emergency stop</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Pop up the red emergency stop button on the teach pendant when the robot is in a safe range of motion</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30078</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">SETPERSOSTENT_FAIL_FAULT</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Set persistent parameter failed because the robot safety mode is in fault</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30079</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">SETPERSOSTENT_FAIL_PARAM_ERR</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Set persistent parameter failed</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">(a) Check the parameter format, whether all are floating point numbers</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30080</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">ROBOT_CABLE_DISCONN</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Robot cable not connected</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">(a) Make sure the cable between Control Box and Robot Arm is correctly connected and it has no damage. (b) Check for loose connections (c) Do a Complete rebooting sequence (d) Update software (e) Contact your local AUBO Robots service provider for assistance Contact your local AUBO Robots service provider for assistance.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30081</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">TP_TOO_SHORT</code></td>
<td style="padding: 6px 8px; vertical-align: top;">The generated trajectory is ignored because it is too short</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">(a) Please check if the added waypoints are coincident (b) If it is an arc movement, please check whether the three points are collinear</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30082</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">INV_KIN_FAIL</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Inverse kinematics solution failed. The target pose may be in a singular position or exceed the joint limits</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">(a) Change the target pose and try moving again</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30083</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">FREEDRIVE_ENABLED</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Freedrive status changed to {}</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30084</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">TP_INV_FAIL_REFERENCE_JOINT_OUT_OF_LIMIT</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Inverse kinematics solution failed. Reference angle [{}] exceeds joint limit [{}].</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30085</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">TP_INV_FAIL_NO_SOLUTION</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Inverse kinematics solution failed. The reference angle [{}] and the target angle [{}] are used as parameters. there is no solution in the calculation of the inverse solution process.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30086</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">SERVO_FAIL_VIOLATION</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Switch servo mode failed because the robot safety mode is in violation</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30087</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">SERVO_FAIL_SYSTEMEMERGENCYSTOP</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Switch servo mode failed because the robot safety mode is in system emergency stop</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30088</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">SERVO_FAIL_ROBOTEMERGENCYSTOP</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Switch servo mode failed because the robot safety mode is in robot emergency stop</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Pop up the red emergency stop button on the teach pendant when the robot is in a safe range of motion</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30089</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">SERVO_FAIL_FAULT</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Switch servo mode failed because the robot safety mode is in fault</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30090</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">FREEDRIVE_FAIL_NO_RUNNING</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Enable handguide mode failed because the robot mode type is {}(not running)</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30091</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">RUNTIME_MACHINE_ERROR</code></td>
<td style="padding: 6px 8px; vertical-align: top;">The state of the running machine is {}, not {}. {} function execution failed because the state is wrong.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30092</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">RESUME_FAR_PAUSE_PT</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Cannot resume from joint position [{}].\nToo far away from paused point [{}].</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30093</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">PAYLOAD_LIGHTER_ERROR</code></td>
<td style="padding: 6px 8px; vertical-align: top;">The payload setting is too small!</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30094</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">PAYLOAD_OVERLOAD_ERROR</code></td>
<td style="padding: 6px 8px; vertical-align: top;">The payload setting is too large!</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30095</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">PAUSE_FAIL_NOT_POSITION_PLAN_MODE</code></td>
<td style="padding: 6px 8px; vertical-align: top;">This motion does not support the pause function. The motion is stopping.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30096</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">TP_PLAN_FAILED_CIRCULAR_WAYPOINTS_COINCIDE</code></td>
<td style="padding: 6px 8px; vertical-align: top;">The planning failed because the three waypoints of the arc were determined to coincide.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Check the circular waypoints to make sure they are different.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30097</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">SERVO_WRONG_SAFETYMODE</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Switch servo mode failed because the robot safety mode is in {}.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Check the circular waypoints to make sure they are different.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30098</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">SET_PERSTPARAM_WRONG_SAFETYMODE</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Set persistent parameter failed because the robot safety mode is in {}</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30099</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">SET_KINPARAM_WRONG_SAFETYMODE</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Set Kinematics Compensate parameters failed because the robot safety mode is in {}</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30100</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">SET_ROBOT_ZERO_WRONG_SAFETYMODE</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Set current joint angles to zero failed because the robot safety mode is in {}</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30101</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">UPFIRMWARE_WRONG_SAFETYMODE</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Firmware update failed because the robot safety mode is in {}</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30102</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">POWERON_WRONG_SAFETYMODE</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Failed to power on because the robot safety mode is in {}</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30103</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">STARTUP_WRONG_SAFETYMODE</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Failed to startup because the robot safety mode is in {}</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30104</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">BACKDRIVE_WRONG_SAFETYMODE</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Failed to backdrive because the robot safety mode is in system emergency stop</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30105</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">SETSIM_WRONG_SAFETYMODE</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Switch sim mode failed because the robot safety mode is in violation</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30106</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">FREEDRIVE_WRONG_SAFETYMODE</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Enable handguide mode failed because the robot safety mode is in wrong safety mode: {}</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30107</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">TP_PLAN_FAILED_JOINT_JUMP_BIGGER</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Inverse kinematics solution failed. The target point and the current point are in different robot configuration spaces.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Add a few more points between the target point and the current point.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30108</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">RUN_PROGRAM_FAILED</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Run program {} failed.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30109</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">FREEDRIVE_FAIL_WRONG_RTMSTATE</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Unable to enter the HandGuide mode as the robot is not currently in a stopped or paused state.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30110</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">SAFEGUARDSTOP_CONFIGURABLE_INPUT</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Configurable safety input is triggered.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30111</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">SAFEGUARDSTOP_3PE</code></td>
<td style="padding: 6px 8px; vertical-align: top;">3PE is triggered.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30112</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">SAFEGUARDSTOP_SI</code></td>
<td style="padding: 6px 8px; vertical-align: top;">SI0/SI1 is triggered.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30200</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">ROBOT_TYPE_CHANGED</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Robot type changed to &#39;{}&#39;, and robot subtype changed to &#39;{}&#39;</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30201</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">LINKMODE_CHANGED</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Link mode changed to {}</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30301</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">ROBOT_SELF_COLLISION</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Detect risk of robot self collision</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30302</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">CONSTANT_INVALID</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Joint torque constants are invalid. HandGuide will be disabled, and the collision protection may be triggered by mistake.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30303</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">GRAVITY_INVALID</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Abnormal value of gravity acceleration sensor. HandGuide will be disabled, and the collision protection may be triggered by mistake.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30304</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">DYNAMICS_INVALID</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Robot dynamics parameters are invalid. HandGuide will be disabled, and the collision protection may be triggered by mistake.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30305</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">FRICTION_INVALID</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Joint friction parameters are invalid. HandGuide will be disabled, and the collision protection may be triggered by mistake.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30306</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">HANDGUIDE_UNDER_DEVELOP</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Robot type of {} function under development. HandGuide will be disabled, and the collision protection may be triggered by mistake.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30307</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">SLOW_DOWN_INFO</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Slow down level changed to {}({}%)</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30308</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">WRONG_JOINT_DESIGNED_LIMIT</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Joint designed ranges exceeds ranges read from hardware interface.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30309</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">FREEDRIVE_IN_SIMULATION</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Enable handguide mode failed because the robot is in simulation mode.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30310</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">ROBOT_STOPPING_TIMEOUT</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Robot stopping timeout.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30311</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">PSTOP_INCORRECT_FORCE_OFFSET</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Protective Stop: Sudden change in force control target position. Force sensor offset may be incorrect or force sensor fault.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30312</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">WRONG_JOINT_SAFETY_LIMIT</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Joint safety ranges exceeds designed ranges.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30401</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">PSTOP_TCP_PLANE_VIOLATION</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Protective Stop: TCP position close to safety plane limits.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30402</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">PSTOP_ELBOW_PLANE_VIOLATION</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Protective Stop: elbow position close to safety plane limits.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30403</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">PSTOP_JOINT_TORQUE_VIOLATION</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Protective Stop: joint{} exceeds torque limit.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30404</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">PSTOP_JOINT_POSITION_VIOLATION</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Protective Stop: joint{} exceeds position limit.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30405</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">PSTOP_JOINT_SPEED_VIOLATION</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Protective Stop: joint{} exceeds speed limit.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30406</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">PSTOP_TCP_SPEED_VIOLATION</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Protective Stop: TCP speed close to safety limits.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30407</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">PSTOP_ELBOW_SPEED_VIOLATION</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Protective Stop: elbow speed close to safety limits.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30408</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">PSTOP_TCP_FORCE_VIOLATION</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Protective Stop: TCP foece close to safety limits.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30409</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">PSTOP_ELBOW_TORQUE_VIOLATION</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Protective Stop: elbow torque close to safety limits.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30410</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">PSTOP_POWER_VIOLATION</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Protective Stop: robot power close to safety limits.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30411</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">PSTOP_MOMENTUM_VIOLATION</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Protective Stop: robot momentum close to safety limits.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30412</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">PSTOP_TCP_CUBE_VIOLATION</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Protective Stop: TCP position close to safety cube.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30413</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">PSTOP_ELBOW_CUBE_VIOLATION</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Protective Stop: TCP position close to safety cube.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30414</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">REDUCE_ELBOW_PLANE_TRIGGER</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Reduce mode: elbow close to safety plane triggers reduction mode.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30415</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">REDUCE_TCP_PLANE_TRIGGER</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Reduce mode: TCP close to safety plane triggers reduction mode.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30416</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">PSTOP_MOVE_OUT_RANGE</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Joint {} has exceeded the limit, please do not continue to move out of the range</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30417</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">RESUME_PAUSE_FAILED</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Resume Failed: Safety mode type is {}</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30418</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">FIRMWARE_UPDATE_FAIL_EMERGENCYSTOP</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Failed to firmware update because the robot safety mode is in {}</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Release emergency stop when the robot is in a safe range of motion</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30419</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">TOOL_SENSOR_CHANGED</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Tool sensor type changed to {}</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30420</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">TOOL_SENSOR_REMOVED</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Tool sensor is removed.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30421</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">CAL_TARGET_CURRENT_ERR</code></td>
<td style="padding: 6px 8px; vertical-align: top;">The calculation of the target current failed. Please try again later.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30422</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">CONVEYOR_MODE_CHANGED</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Conveyor{}: track mode changed to {}, track item id is {}</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30423</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">CONVEYOR_ENQUEUE</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Conveyor{}: the queue has been changed, item{} is enqueue</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30424</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">CONVEYOR_DEQUEUE_FINISH</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Conveyor{}: the queue has been changed, item{} dequeue due to track finished</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30425</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">CONVEYOR_DEQUEUE_STARTWINDOW</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Conveyor{}: the queue has been changed, item{} dequeue due to exceeds startwindow</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30426</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">CONVEYOR_DEQUEUE_LIMIT</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Conveyor{}: the queue has been changed, item{} dequeue due to exceed limit area</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30427</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">CONVEYOR_DEQUEUE_CLEAR</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Conveyor{}: item queue is cleared</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30428</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">CONVEYOR_NEXT_TRACK</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Conveyor{}: item{} inside the start window that can be tracked</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30429</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">CONVEYOR_EXCEED_LIMIT</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Conveyor{}: item{} exceeds the limit area during tracking</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30430</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">WRONG_POWER_SAFETY_LIMIT</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Robot power safety value exceeds designed value.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30431</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">WRONG_POWER_DESIGNED_LIMIT</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Power designed value exceeds value read from hardware interface.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30432</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">TOOL_SENSOR_STATUS_CHANGED</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Tool sensor status changed to {}</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30433</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">COLLISION_THRESHOLD_INVALID</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Robot collision threshold parameters are invalid.Please reidentify the threshold or modify the configuration to ensure that it does not cause accidental collisions.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30434</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">GRIPPER_DISCONNECT</code></td>
<td style="padding: 6px 8px; vertical-align: top;">The gripper {} is disconnected.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30435</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">GRIPPER_UNKNOWN_FAULT</code></td>
<td style="padding: 6px 8px; vertical-align: top;">There is an unknown fault with the gripper {}</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30436</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">GRIPPER_CURRENT_ANOMALY_FAULT</code></td>
<td style="padding: 6px 8px; vertical-align: top;">There is an abnormal current fault with the gripper {}</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30437</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">GRIPPER_VOLTAGE_ANOMALY_FAULT</code></td>
<td style="padding: 6px 8px; vertical-align: top;">There is an abnormal voltage fault with the gripper {}</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30438</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">GRIPPER_OVER_TEMPERATURE_FAULT</code></td>
<td style="padding: 6px 8px; vertical-align: top;">There is an over-temperature fault with the gripper {}</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30439</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">GRIPPER_INTERNAL_FAULT</code></td>
<td style="padding: 6px 8px; vertical-align: top;">There is an internal fault with the gripper {}</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30440</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">GRIPPER_COMMUNICATION_FAULT</code></td>
<td style="padding: 6px 8px; vertical-align: top;">There is an communication fault with the gripper {}</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30441</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">GRIPPER_CONTROL_COMMAND_FAULT</code></td>
<td style="padding: 6px 8px; vertical-align: top;">There is an control command fault with the gripper {}</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30442</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">GRIPPER_ENABLE_FAULT</code></td>
<td style="padding: 6px 8px; vertical-align: top;">There is an enable fault with the gripper {}</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30443</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">WRIST_SINGULARITY_RISK</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Wrist singularity detected. Linear motion may cause excessive joint speed.Adjust robot posture to avoid J5 near 0° or 180°, or use joint motion instead of linear motion.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30444</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">PSTOP_PATH_OFFSET_OVER_LIMIT</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Protective Stop: the offset of the robot has exceeded the limit.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30445</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EXT_AXIS_SET_PARAM_FAILED_BUSY</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Set external axis parameter {} failed because the robot mode is in {}. Please power off the robot before changing this parameter.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Power off the robot and try again.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30446</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">WRONG_JOINT_POS_LIMIT</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Joint limit max pos less than min pos.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30447</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">WRONG_JOINT_VEL_LIMIT</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Joint limit max vel is invalid.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30448</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">AUTO_RESUME_FAR_PAUSE_PT</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Robot is still paused after switching to automatic mode. Current joint position [{}] is too far away from pause position [{}]. Resuming directly may cause collision.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Move the robot back to the pause position or stop the program before resuming.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30449</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">CONVEYOR_TRACK_CAPACITY_EXCEEDED</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Conveyor{}: item{} tracking capacity exceeded, tracking stop started. Capacity usage is {}%, actual conveyor speed is {} m/s.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Reduce conveyor speed, shorten tracking distance, or adjust tracking posture.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">30450</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">JACOBIAN_SINGULARITY_RISK</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Jacobian singularity risk detected during Cartesian linear motion. Continuing linear motion may cause excessive joint speed.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">Move away from this area, change robot posture, or avoid linear motion through this pose.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
</tbody>
</table>
</div>

## 工具错误 (40001 - 40034)

<div style="overflow-x: auto; width: 100%;">
<table style="min-width: 1280px; width: 100%; table-layout: fixed; border-collapse: collapse; word-break: break-word;">
<thead>
<tr>
<th style="width: 72px; padding: 6px 8px; vertical-align: top;">错误码</th>
<th style="width: 180px; padding: 6px 8px; vertical-align: top;">名称</th>
<th style="padding: 6px 8px; vertical-align: top;">描述</th>
<th style="padding: 6px 8px; vertical-align: top;">描述(中文)</th>
<th style="padding: 6px 8px; vertical-align: top;">建议</th>
<th style="padding: 6px 8px; vertical-align: top;">报错软件判断逻辑</th>
<th style="padding: 6px 8px; vertical-align: top;">维修排查点</th>
</tr>
</thead>
<tbody>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">40001</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">TOOL_FLASH_VERIFY_FAILED</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Flash write verify failed</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">40002</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">TOOL_PROGRAM_CRC_FAILED</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Program flash checksum failed during bootloading</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">40003</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">TOOL_PROGRAM_CRC_FAILED2</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Program flash checksum failed at runtime</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">40004</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">TOOL_ID_UNDIFINED</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Tool ID is undefined</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">40005</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">TOOL_ILLEGAL_BL_CMD</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Illegal bootloader command</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">40006</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">TOOL_FW_WRONG</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Wrong firmware at the joint</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">40007</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">TOOL_HW_INVALID</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Invalid hardware revision</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">40011</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">TOOL_SHORT_CURCUIT_H</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Short circuit detected on Digital Output: {} high side</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">40012</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">TOOL_SHORT_CURCUIT_L</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Short circuit detected on Digital Output: {} low side</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">40013</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">TOOL_AVERAGE_CURR_HIGH</code></td>
<td style="padding: 6px 8px; vertical-align: top;">10 second Average tool IO Current of {} A is outside of the allowed range.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">40014</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">TOOL_POWER_PIN_OVER_CURR</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Current of {} A on the POWER pin is outside of the allowed range.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">40015</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">TOOL_DOUT_PIN_OVER_CURR</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Current of {} A on the Digital Output pins is outside of the allowed range.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">40016</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">TOOL_GROUND_PIN_OVER_CURR</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Current of {} A on the ground pin is outside of the allowed range.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">40021</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">TOOL_RX_FRAMING</code></td>
<td style="padding: 6px 8px; vertical-align: top;">RX framing error</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">40022</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">TOOL_RX_PARITY</code></td>
<td style="padding: 6px 8px; vertical-align: top;">RX Parity error</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">40031</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">TOOL_48V_LOW</code></td>
<td style="padding: 6px 8px; vertical-align: top;">48V input is too low</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">40032</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">TOOL_48V_HIGH</code></td>
<td style="padding: 6px 8px; vertical-align: top;">48V input is too high</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">40033</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">TOOL_ERR_OFFLINE</code></td>
<td style="padding: 6px 8px; vertical-align: top;">tool error: tool may be offline</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">(a) Check tool&#39;s hardware. (b) Check joint&#39;s id.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">40034</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">TOOL_ERR_BOOTLOADER</code></td>
<td style="padding: 6px 8px; vertical-align: top;">tool error: The tool is in bootloader mode. Retry firmware update.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
</tbody>
</table>
</div>

## 工具扩展错误 (40101 - 40200)

<div style="overflow-x: auto; width: 100%;">
<table style="min-width: 1280px; width: 100%; table-layout: fixed; border-collapse: collapse; word-break: break-word;">
<thead>
<tr>
<th style="width: 72px; padding: 6px 8px; vertical-align: top;">错误码</th>
<th style="width: 180px; padding: 6px 8px; vertical-align: top;">名称</th>
<th style="padding: 6px 8px; vertical-align: top;">描述</th>
<th style="padding: 6px 8px; vertical-align: top;">描述(中文)</th>
<th style="padding: 6px 8px; vertical-align: top;">建议</th>
<th style="padding: 6px 8px; vertical-align: top;">报错软件判断逻辑</th>
<th style="padding: 6px 8px; vertical-align: top;">维修排查点</th>
</tr>
</thead>
<tbody>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">40101</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_TOOL_EC_LOW_VOLTAGE</code></td>
<td style="padding: 6px 8px; vertical-align: top;">tool error: low voltage</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">check tool power supply voltage</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">40102</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_TOOL_EC_FORCESENSOR_COMM</code></td>
<td style="padding: 6px 8px; vertical-align: top;">tool error: external force sensor communication error</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">check external force sensor communication connection</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">40103</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_TOOL_485_SENDFULL_COMM</code></td>
<td style="padding: 6px 8px; vertical-align: top;">tool error: 485 transparent transmission buffer full</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">check 485 communication load and transmission frequency</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">40104</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_TOOL_FORCESENSOR_FILTER_ZERO</code></td>
<td style="padding: 6px 8px; vertical-align: top;">tool error: force sensor filter parameter is zero</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">check force sensor filter parameter configuration</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">40200</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_TOOL_EC_UNKNOWN</code></td>
<td style="padding: 6px 8px; vertical-align: top;">tool error: unknown error</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">check controller logs and hardware status</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
</tbody>
</table>
</div>

## 基座错误 (50001 - 50003)

<div style="overflow-x: auto; width: 100%;">
<table style="min-width: 1280px; width: 100%; table-layout: fixed; border-collapse: collapse; word-break: break-word;">
<thead>
<tr>
<th style="width: 72px; padding: 6px 8px; vertical-align: top;">错误码</th>
<th style="width: 180px; padding: 6px 8px; vertical-align: top;">名称</th>
<th style="padding: 6px 8px; vertical-align: top;">描述</th>
<th style="padding: 6px 8px; vertical-align: top;">描述(中文)</th>
<th style="padding: 6px 8px; vertical-align: top;">建议</th>
<th style="padding: 6px 8px; vertical-align: top;">报错软件判断逻辑</th>
<th style="padding: 6px 8px; vertical-align: top;">维修排查点</th>
</tr>
</thead>
<tbody>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">50001</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">PKG_LOST</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Lost package from pedestal</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">50002</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">PEDSTRAL_OFFLINE</code></td>
<td style="padding: 6px 8px; vertical-align: top;">pedestal error: pedestal may be offline</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">(a) Check pedestal&#39;s hardware. (b) Check pedestal&#39;s id.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">50003</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">PEDESTAL_ERR_BOOTLOADER</code></td>
<td style="padding: 6px 8px; vertical-align: top;">pedestal error: The pedestal is in bootloader mode. Retry firmware update.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
</tbody>
</table>
</div>

## 基座扩展错误 (50101 - 50200)

<div style="overflow-x: auto; width: 100%;">
<table style="min-width: 1280px; width: 100%; table-layout: fixed; border-collapse: collapse; word-break: break-word;">
<thead>
<tr>
<th style="width: 72px; padding: 6px 8px; vertical-align: top;">错误码</th>
<th style="width: 180px; padding: 6px 8px; vertical-align: top;">名称</th>
<th style="padding: 6px 8px; vertical-align: top;">描述</th>
<th style="padding: 6px 8px; vertical-align: top;">描述(中文)</th>
<th style="padding: 6px 8px; vertical-align: top;">建议</th>
<th style="padding: 6px 8px; vertical-align: top;">报错软件判断逻辑</th>
<th style="padding: 6px 8px; vertical-align: top;">维修排查点</th>
</tr>
</thead>
<tbody>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">50101</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_BASE_EC_LOW_VOLTAGE</code></td>
<td style="padding: 6px 8px; vertical-align: top;">pedstral error: low voltage</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">check power supply voltage and battery status</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">50102</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_BASE_EC_OVER_TEMPERATURE_RES</code></td>
<td style="padding: 6px 8px; vertical-align: top;">pedstral error: resistor over temperature</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">check braking resistor temperature and cooling condition</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">50103</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_BASE_EC_OVER_TARGET_BRAKE_OPEN_VOLT</code></td>
<td style="padding: 6px 8px; vertical-align: top;">pedstral error: input voltage close to or exceeds regenerative brake activation voltage</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">check input power voltage and regenerative braking configuration</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">50104</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_BASE_EC_RES_BREAKAGE</code></td>
<td style="padding: 6px 8px; vertical-align: top;">pedstral error: brake resistor breakage</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">check whether the brake resistor is disconnected or damaged</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">50105</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_BASE_EC_IMU_CALIBRATE</code></td>
<td style="padding: 6px 8px; vertical-align: top;">pedstral error: IMU calibration required</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">perform IMU calibration according to maintenance procedure</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">50106</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_BASE_EC_TEMP_SENSOR_SHORT</code></td>
<td style="padding: 6px 8px; vertical-align: top;">pedstral error: temperature sensor short circuit</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">check temperature sensor wiring and solder joints for short circuit</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">50107</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_BASE_EC_TEMP_SENSOR_BREAK</code></td>
<td style="padding: 6px 8px; vertical-align: top;">pedstral error: temperature sensor open circuit</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">check temperature sensor connection and cable continuity</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">50108</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_BASE_EC_96V_INSTANT_OVER_VOLTAGE</code></td>
<td style="padding: 6px 8px; vertical-align: top;">pedstral error: 96V instantaneous over voltage after regenerative braking</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">check regenerative braking behavior and power bus voltage</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">50200</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">EX_BASE_EC_UNKNOWN</code></td>
<td style="padding: 6px 8px; vertical-align: top;">pedstral error: unknown error</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;">check controller logs and hardware status</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
</tbody>
</table>
</div>

## 硬件接口错误 (60001 - 60080)

<div style="overflow-x: auto; width: 100%;">
<table style="min-width: 1280px; width: 100%; table-layout: fixed; border-collapse: collapse; word-break: break-word;">
<thead>
<tr>
<th style="width: 72px; padding: 6px 8px; vertical-align: top;">错误码</th>
<th style="width: 180px; padding: 6px 8px; vertical-align: top;">名称</th>
<th style="padding: 6px 8px; vertical-align: top;">描述</th>
<th style="padding: 6px 8px; vertical-align: top;">描述(中文)</th>
<th style="padding: 6px 8px; vertical-align: top;">建议</th>
<th style="padding: 6px 8px; vertical-align: top;">报错软件判断逻辑</th>
<th style="padding: 6px 8px; vertical-align: top;">维修排查点</th>
</tr>
</thead>
<tbody>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">60001</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">HW_SCB_SETUP_FAILED</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Setup of Interface Board failed</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">60002</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">HW_PKG_CNT_DISAGEE</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Packet counter disagreements</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">60003</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">HW_SCB_DISCONNECT</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Connection to Interface Board lost</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">60004</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">HW_SCB_PKG_LOST</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Package lost from Interface Board</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">60005</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">HW_SCB_CONN_INIT_FAILED</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Ethernet connection initialization with Interface Board failed</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">60006</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">HW_LOST_JOINT_PKG</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Lost package from joint  {}</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">60007</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">HW_LOST_TOOL_PKG</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Lost package from tool</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">60008</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">HW_JOINT_PKG_CNT_DISAGREE</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Packet counter disagreement in packet from joint {}</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">60009</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">HW_TOOL_PKG_CNT_DISAGREE</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Packet counter disagreement in packet from tool</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">60011</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">HW_JOINTS_FAULT</code></td>
<td style="padding: 6px 8px; vertical-align: top;">{} joint entered the Fault State</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">60012</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">HW_JOINTS_VIOLATION</code></td>
<td style="padding: 6px 8px; vertical-align: top;">{} joint entered the Violation State</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">60013</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">HW_TP_FAULT</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Teach Pendant entered the Fault State</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">60014</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">HW_TP_VIOLATION</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Teach Pendant entered the Violation State</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">60021</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">HW_JOINT_MV_TOO_FAR</code></td>
<td style="padding: 6px 8px; vertical-align: top;">{} joint moved too far before robot entered RUNNING State</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">60022</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">HW_JOINT_STOP_NOT_FAST</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Joint Not stopping fast enough</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">60023</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">HW_JOINT_MV_LIMIT</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Joint moved more than allowable limit</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">60024</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">HW_FT_SENSOR_DATA_INVALID</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Force-Torque Sensor data invalid</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">60025</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">HW_NO_FT_SENSOR</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Force-Torque sensor is expected, but it cannot be detected</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">60026</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">HW_FT_SENSOR_NOT_CALIB</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Force-Torque sensor is detected but not calibrated</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">60030</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">HW_RELEASE_BRAKE_FAILED</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Robot was not able to brake release, see log for details</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">60040</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">HW_OVERCURR_SHUTDOWN</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Overcurrent shutdown</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">60050</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">HW_ENERGEY_SURPLUS</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Energy surplus shutdown</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">60060</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">HW_IDLE_POWER_HIGH</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Idle power consumption to high</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">60071</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">HW_ENTER_COLLISION_TIMEOUT</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Enter collision stop procedure timeout</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">60072</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">HW_POWERON_TIMEOUT</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Poweron robot timeout</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">60073</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">HW_NO_NIC_FOUND</code></td>
<td style="padding: 6px 8px; vertical-align: top;">No network cards found.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">60074</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">HW_IFB_NOT_FOUND</code></td>
<td style="padding: 6px 8px; vertical-align: top;">No Interface Board found.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">60075</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">HW_IFB_BOOTLOAD</code></td>
<td style="padding: 6px 8px; vertical-align: top;">The Interface Board is in bootloader mode. Update firmware firstly.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">60076</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">HW_TOOL_NOT_FOUND</code></td>
<td style="padding: 6px 8px; vertical-align: top;">No Tool Board found.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">60077</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">HW_BASE_NOT_FOUND</code></td>
<td style="padding: 6px 8px; vertical-align: top;">No Base Board found.</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">60078</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">HW_BRINGUP_TIMEOUT</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Poweron robot timeout</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">60079</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">HW_COLLISION_RECOVERY_FAILED</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Collision recovery failed</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
<tr>
<td style="padding: 6px 8px; vertical-align: top;">60080</td>
<td style="padding: 6px 8px; vertical-align: top;"><code style="white-space: normal; overflow-wrap: anywhere;">HW_TP_ENABLED</code></td>
<td style="padding: 6px 8px; vertical-align: top;">Teach pendant enabled status changed to {}</td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
<td style="padding: 6px 8px; vertical-align: top;"></td>
</tr>
</tbody>
</table>
</div>

