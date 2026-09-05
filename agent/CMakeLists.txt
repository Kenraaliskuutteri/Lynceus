cmake_minimum_required(VERSION 3.10)
project(lynceus-agent C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

find_package(PkgConfig REQUIRED)
pkg_check_modules(LWS REQUIRED libwebsockets)

add_executable(lynceus-agent
    src/main.c
    src/collector.c
    src/websocket_client.c
    src/config.c
    src/daemon.c
)

target_include_directories(lynceus-agent PRIVATE include ${LWS_INCLUDE_DIRS})
target_link_libraries(lynceus-agent PRIVATE ${LWS_LIBRARIES})
target_compile_options(lynceus-agent PRIVATE ${LWS_CFLAGS_OTHER} -Wall -Wextra)
install(TARGETS lynceus-agent RUNTIME DESTINATION bin)