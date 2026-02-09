#pragma once

#include <array>
#include <complex>

class Modem {

  public:
    std::complex<float> modulate(uint16_t symbol) {
        return lookup_table[symbol];
    }

    uint16_t demodulate(std::complex<float> input) {
        float shortest_distance = 100.0;
        uint16_t closest_symbol;
        for (int i = 0; i < lookup_table.size(); ++i) {

            // abs (euclidean norm) is slower to compute
            // if abs(z1) > abs(z2) then norm(z1) > abs(z2)
            // meaning that this is fine
            // https://en.cppreference.com/w/cpp/numeric/complex/norm.html
            float distance = std::norm(lookup_table[i] - input);
            if (distance < shortest_distance) {
                shortest_distance = distance;
                closest_symbol = i;
            }
        }
        return closest_symbol;
    };

    friend std::ostream &operator<<(std::ostream &os, const Modem &modem) {
        for (int i = 0; i < modem.constellation.size(); ++i) {
            for (int j = 0; j < modem.constellation[i].size(); ++j) {
                os << " " << modem.constellation[i][j];
            }
            os << "\n";
        }

        for (int i = 0; i < modem.lookup_table.size(); ++i) {
            os << modem.lookup_table[i];
        }

        return os;
    }

  protected:
    // TODO: This is hardcoded for 16-QAM. Make a template?
    std::array<std::array<int, 4>, 4> constellation;
    std::array<std::complex<float>, 16> lookup_table;
};

class Mqam : public Modem {

  public:
    Mqam(uint8_t size);

  private:
    void generate_constellation(uint8_t size);
    void generate_lookup_table(uint8_t size);
};
