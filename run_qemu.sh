#!/bin/bash
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cmake -S "$SCRIPT_DIR/firmware" -B "$SCRIPT_DIR/firmware/build" \
    -DCMAKE_TOOLCHAIN_FILE="$SCRIPT_DIR/firmware/cmake/toolchain-arm-none-eabi.cmake" \
    -G Ninja 2>&1
cmake --build "$SCRIPT_DIR/firmware/build" 2>&1
echo "Starting QEMU... Press Ctrl+A X to exit"
qemu-system-arm \
    -M stm32vldiscovery \
    -kernel "$SCRIPT_DIR/firmware/build/ecu_firmware.elf" \
    -semihosting-config enable=on,target=native \
    -nographic
