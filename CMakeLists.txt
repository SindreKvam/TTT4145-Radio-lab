
cmake_minimum_required(VERSION 3.22)
project(RadioLab)


# GoogleTest requires at least C++17
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

include(FetchContent)


# GoogleTest as testing framework
FetchContent_Declare(
  googletest
  URL https://github.com/google/googletest/archive/03597a01ee50ed33e9dfd640b249b4be3799d395.zip
)
# For Windows: Prevent overriding the parent project's compiler/linker settings
set(gtest_force_shared_crt ON CACHE BOOL "" FORCE)
FetchContent_MakeAvailable(googletest)

# For plotting using Matplot++
FetchContent_Declare(matplotplusplus
        GIT_REPOSITORY https://github.com/alandefreitas/matplotplusplus.git
        GIT_TAG master)
FetchContent_MakeAvailable(matplotplusplus)

# Qt for real-time plotting
find_package(Qt5 COMPONENTS Widgets PrintSupport REQUIRED)


# ---------- Applications ----------
# TX
add_executable(radio_tx src/main_tx.cpp src/core/fir.cpp)
target_include_directories(radio_tx PUBLIC include)
target_link_libraries(radio_tx iio)

# RX
add_executable(radio_rx
    src/main_rx.cpp
    src/core/fir.cpp
    src/radio/radio_rx.cpp
    src/gui/window.cpp
    src/gui/qcustomplot.cpp
)
set_target_properties(radio_rx PROPERTIES AUTOMOC ON)
target_include_directories(radio_rx PUBLIC include)
target_link_libraries(radio_rx iio matplot Qt5::Widgets Qt5::PrintSupport)

# Testing
enable_testing()

add_executable(
  unittests
  # Test files
  tests/core_test.cpp
  tests/tx_tests.cpp
  # Source files
  src/core/fir.cpp
  src/core/root_raised_cosine.cpp
  src/tx/fault_protection.cpp
  src/tx/modulators.cpp
)
target_link_libraries(
  unittests
  GTest::gtest_main
  matplot
)

include(GoogleTest)
gtest_discover_tests(unittests)
