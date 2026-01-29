# TTT4145 - Radio Communications - Lab

The purpose of the Lab in the course TTT4145 is to
establish a connection between two ADALM-PLUTO software defined radios.

## Development

Formatting is done using `clang-format`.

## Requirements

On debian based linux distros, install the following dependencies:
```
sudo apt install gnuplot libiio-dev libiio-utils qtbase5-dev
```

## Building and testing

To create a build directory and install dependencies, run the following command
while in the root folder.
```
cmake -S . -B build -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
ln -s build/compile_commands.json
```

Run the following line to compile the code.
```
cmake --build build
```

To run unit-tests, run the following command:
```
ctest --test-dir build
```
