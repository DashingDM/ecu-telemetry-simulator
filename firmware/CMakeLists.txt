cmake_minimum_required(VERSION 3.20)

project(ecu_firmware C ASM)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_C_EXTENSIONS OFF)

if(NOT CMAKE_C_COMPILER_ID MATCHES "GNU")
  message(FATAL_ERROR "Use the arm-none-eabi-gcc toolchain file to build the firmware.")
endif()

set(FREERTOS_PORT GCC_ARM_CM3 CACHE STRING "" FORCE)
set(FREERTOS_KERNEL_PATH "${CMAKE_CURRENT_LIST_DIR}/../FreeRTOS/FreeRTOS-Kernel")

add_library(freertos_config INTERFACE)
target_include_directories(freertos_config SYSTEM INTERFACE ${CMAKE_CURRENT_LIST_DIR}/include)

add_subdirectory(${FREERTOS_KERNEL_PATH} freertos-kernel-build)

target_compile_options(freertos_kernel PRIVATE
  -mcpu=cortex-m3
  -mthumb
  -ffreestanding
  -ffunction-sections
  -fdata-sections
  -fno-common
)

target_compile_options(freertos_kernel_port PRIVATE
  -mcpu=cortex-m3
  -mthumb
  -ffreestanding
  -ffunction-sections
  -fdata-sections
  -fno-common
)

add_executable(ecu_firmware.elf
  src/startup_stm32f100rb.s
  src/console.c
  src/hooks.c
  src/libc_shim.c
  src/main.c
  src/semihost.c
  src/system_stm32f100rb.c
)

target_include_directories(ecu_firmware.elf PRIVATE ${CMAKE_CURRENT_LIST_DIR}/include)
target_compile_options(ecu_firmware.elf PRIVATE
  -mcpu=cortex-m3
  -mthumb
  -ffreestanding
  -ffunction-sections
  -fdata-sections
  -fno-common
  -Wall
  -Wextra
  -Wpedantic
  -Wno-unused-parameter
)

target_link_options(ecu_firmware.elf PRIVATE
  -mcpu=cortex-m3
  -mthumb
  -T${CMAKE_CURRENT_LIST_DIR}/ld/stm32f100rb.ld
  -nostdlib
  -Wl,--gc-sections
  -Wl,-Map=${CMAKE_CURRENT_BINARY_DIR}/ecu_firmware.map
)

target_link_libraries(ecu_firmware.elf PRIVATE
  freertos_kernel
  freertos_config
  gcc
)

add_custom_command(TARGET ecu_firmware.elf POST_BUILD
  COMMAND arm-none-eabi-objcopy -O binary $<TARGET_FILE:ecu_firmware.elf> ${CMAKE_CURRENT_BINARY_DIR}/ecu_firmware.bin
  BYPRODUCTS ${CMAKE_CURRENT_BINARY_DIR}/ecu_firmware.bin
  COMMENT "Generating binary image"
)
