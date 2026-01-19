#pragma once

#include <vector>
#include <cstdint>
#include <iostream>
#include <cmath>

template <typename T>
void print_vector(const std::vector<T>& v)
{
    for (const auto& x : v)
    {
        std::cout << x << " ";
    }
    std::cout << std::endl;
}

std::vector<uint16_t> generate_random_message(int16_t len_of_frame);
void format_message(std::vector<uint16_t> msg);
void fault_protect_frame(std::vector<uint16_t> message);
