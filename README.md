# TTT4145 - Radio Communications - Lab

The purpose of the Lab in the course TTT4145 is to
establish a connection between two ADALM-PLUTO software defined radios.

## Building and testing

To build the firmware. Run the following command while in the root folder:
```
cmake -S . -B build
cmake --build build
```

To run unit-tests, run the following command:
```
ctest --test-dir build
```
