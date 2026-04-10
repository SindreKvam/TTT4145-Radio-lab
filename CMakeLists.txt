
cmake_minimum_required(VERSION 3.22)
project(RadioLab)

# GoogleTest requires at least C++17
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# ---------- Python bindings (built by pip / scikit-build-core) ----------
option(BUILD_PYTHON_BINDINGS "Build pybind11 python bindings" OFF)

if(BUILD_PYTHON_BINDINGS)
    find_package(Python3 COMPONENTS Interpreter Development REQUIRED)
    find_package(pybind11 REQUIRED HINTS "${Python3_SITELIB}")

    pybind11_add_module(modem
        src/modem/modem.cpp
    )
    pybind11_add_module(fir_filter
        src/core/fir.cpp
        src/core/root_raised_cosine.cpp
    )
    pybind11_add_module(pll
        src/pll/pll.cpp
    )
    pybind11_add_module(hamming
        src/fault_protection/fault_protection.cpp
    )
    target_compile_definitions(modem PRIVATE PYBIND11=1)
    target_compile_definitions(fir_filter PRIVATE PYBIND11=1)
    target_compile_definitions(pll PRIVATE PYBIND11=1)
    target_compile_definitions(hamming PRIVATE PYBIND11=1)
    target_include_directories(modem PRIVATE include src)
    target_include_directories(fir_filter PRIVATE include src)
    target_include_directories(pll PRIVATE include src)
    target_include_directories(hamming PRIVATE include src)

    install(TARGETS modem LIBRARY DESTINATION . COMPONENT python)
    install(TARGETS fir_filter LIBRARY DESTINATION . COMPONENT python)
    install(TARGETS pll LIBRARY DESTINATION . COMPONENT python)
    install(TARGETS hamming LIBRARY DESTINATION . COMPONENT python)

# ---------- Native build (cmake ..) ----------
else()
    include(FetchContent)

    # GoogleTest
    FetchContent_Declare(
        googletest
        URL https://github.com/google/googletest/archive/03597a01ee50ed33e9dfd640b249b4be3799d395.zip
    )
    set(gtest_force_shared_crt ON CACHE BOOL "" FORCE)
    FetchContent_MakeAvailable(googletest)

    # Matplot++ (used by unit tests)
    FetchContent_Declare(matplotplusplus
        GIT_REPOSITORY https://github.com/alandefreitas/matplotplusplus.git
        GIT_TAG master
    )
    FetchContent_MakeAvailable(matplotplusplus)

    # Qt5 (used by the real-time GUI)
    find_package(Qt5 COMPONENTS Widgets PrintSupport REQUIRED)

    # TX stub
    add_executable(radio_tx src/main_tx.cpp src/core/fir.cpp)
    target_include_directories(radio_tx PUBLIC include)
    target_link_libraries(radio_tx iio)

    # Full-duplex RX+TX with Qt GUI
    add_executable(radio_rxtx
        src/main_rxtx.cpp
        src/core/fir.cpp
        src/core/root_raised_cosine.cpp
        src/radio/pluto_sdr.cpp
        src/modem/modem.cpp
        src/gui/window.cpp
        src/gui/qcustomplot.cpp
    )
    set_target_properties(radio_rxtx PROPERTIES AUTOMOC ON)
    target_include_directories(radio_rxtx PUBLIC include src)
    target_link_libraries(radio_rxtx iio Qt5::Widgets Qt5::PrintSupport)

    # Unit tests
    enable_testing()

    add_executable(unittests
        tests/core_test.cpp
        tests/tx_tests.cpp
        tests/spsc_test.cpp
        src/core/fir.cpp
        src/core/root_raised_cosine.cpp
        src/modem/modem.cpp
    )
    target_include_directories(unittests PUBLIC include src)
    target_link_libraries(unittests GTest::gtest_main matplot)

    include(GoogleTest)
    gtest_discover_tests(unittests)

endif()
