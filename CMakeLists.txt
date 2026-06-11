cmake_minimum_required(VERSION 3.16)
project(ecu_telemetry_simulator C)
set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

add_executable(ecu_simulator
    src/host_main.c
    src/ecu_sim.c
    src/queue.c
)
target_include_directories(ecu_simulator PRIVATE src)
target_link_libraries(ecu_simulator PRIVATE pthread m)
