#include "pll.h"

#include <algorithm>
#include <cmath>
#include <complex>
#include <cstddef>
#include <cstdint>
#include <limits>
#include <stdexcept>
#include <vector>

namespace {

uint16_t demodulate_symbol(const std::complex<float> &symbol,
                           const std::vector<std::complex<float>> &lut) {
    uint16_t closest_index = 0;
    float smallest_error = std::numeric_limits<float>::max();

    for (uint16_t i = 0; i < lut.size(); i++) {
        const float error = std::abs(lut[i] - symbol);
        if (error < smallest_error) {
            smallest_error = error;
            closest_index = i;
        }
    }

    return closest_index;
}

} // namespace

Pll::Pll(float k_p, float k_i) : k_p(k_p), k_i(k_i) {}

std::vector<std::complex<float>>
Pll::phase_lock(const std::vector<std::complex<float>> &signal,
                const std::vector<std::complex<float>> &lut,
                const std::vector<std::complex<float>> &pll_preamble) const {
    if (lut.empty()) {
        throw std::invalid_argument("LUT must not be empty");
    }

    std::vector<std::complex<float>> phase_locked_data(signal.size());

    float theta = 0.0F;
    float integrator = 0.0F;
    const size_t preamble_len = pll_preamble.size();

    for (size_t i = 0; i < signal.size(); i++) {
        const std::complex<float> derot =
            signal[i] * std::exp(std::complex<float>(0.0F, -theta));
        phase_locked_data[i] = derot;

        std::complex<float> closest_symbol;
        if (i < preamble_len) {
            closest_symbol = pll_preamble[i];
        } else {
            const uint16_t decision = demodulate_symbol(derot, lut);
            closest_symbol = lut[decision];
        }

        const float e = std::imag(derot * std::conj(closest_symbol));

        integrator += k_i * e;
        theta += integrator + k_p * e;
    }

    return phase_locked_data;
}

std::tuple<std::vector<std::complex<float>>, std::vector<float>,
           std::vector<float>>
Pll::phase_lock_with_stats(
    const std::vector<std::complex<float>> &signal,
    const std::vector<std::complex<float>> &lut,
    const std::vector<std::complex<float>> &pll_preamble) const {
    if (lut.empty()) {
        throw std::invalid_argument("LUT must not be empty");
    }

    std::vector<std::complex<float>> phase_locked_data(signal.size());
    std::vector<float> phase_error(signal.size(), 0.0F);
    std::vector<float> theta_history(signal.size(), 0.0F);

    float theta = 0.0F;
    float integrator = 0.0F;
    const size_t preamble_len = pll_preamble.size();

    for (size_t i = 0; i < signal.size(); i++) {
        const std::complex<float> derot =
            signal[i] * std::exp(std::complex<float>(0.0F, -theta));
        phase_locked_data[i] = derot;
        theta_history[i] = theta;

        std::complex<float> closest_symbol;
        if (i < preamble_len) {
            closest_symbol = pll_preamble[i];
        } else {
            const uint16_t decision = demodulate_symbol(derot, lut);
            closest_symbol = lut[decision];
        }

        const float e = std::imag(derot * std::conj(closest_symbol));
        phase_error[i] = e;

        integrator += k_i * e;
        theta += integrator + k_p * e;
    }

    return {phase_locked_data, phase_error, theta_history};
}

#ifdef PYBIND11

#include <pybind11/complex.h>
#include <pybind11/numpy.h>
#include <pybind11/pybind11.h>

namespace py = pybind11;

PYBIND11_MODULE(pll, m, py::mod_gil_not_used()) {
    m.doc() = "Phase locked loop helpers";

    py::class_<Pll>(m, "Pll")
        .def(py::init<float, float>(), py::arg("k_p") = 0.0222F,
             py::arg("k_i") = 0.00024F)
        .def(
            "phase_locked_loop_array",
            [](const Pll &pll,
               py::array_t<std::complex<float>,
                           py::array::c_style | py::array::forcecast>
                   samples,
               py::array_t<std::complex<float>,
                           py::array::c_style | py::array::forcecast>
                   lut,
               py::object pll_preamble_obj) {
                const py::buffer_info samples_info = samples.request();
                const py::buffer_info lut_info = lut.request();

                auto *samples_ptr =
                    static_cast<std::complex<float> *>(samples_info.ptr);
                auto *lut_ptr =
                    static_cast<std::complex<float> *>(lut_info.ptr);

                std::vector<std::complex<float>> samples_vec(
                    samples_ptr, samples_ptr + samples_info.size);
                std::vector<std::complex<float>> lut_vec(
                    lut_ptr, lut_ptr + lut_info.size);

                std::vector<std::complex<float>> preamble_vec;
                if (!pll_preamble_obj.is_none()) {
                    py::array_t<std::complex<float>,
                                py::array::c_style | py::array::forcecast>
                        preamble_array = pll_preamble_obj.cast<py::array_t<
                            std::complex<float>,
                            py::array::c_style | py::array::forcecast>>();
                    const py::buffer_info preamble_info =
                        preamble_array.request();
                    auto *preamble_ptr =
                        static_cast<std::complex<float> *>(preamble_info.ptr);
                    preamble_vec.assign(preamble_ptr,
                                        preamble_ptr + preamble_info.size);
                }

                std::vector<std::complex<float>> out_vec;
                {
                    py::gil_scoped_release release;
                    out_vec =
                        pll.phase_lock(samples_vec, lut_vec, preamble_vec);
                }

                py::array_t<std::complex<float>> out(samples_info.shape);
                py::buffer_info out_info = out.request();
                auto *out_ptr =
                    static_cast<std::complex<float> *>(out_info.ptr);

                std::copy(out_vec.begin(), out_vec.end(), out_ptr);
                return out;
            },
            py::arg("samples"), py::arg("lut"),
            py::arg("pll_preamble") = py::none(),
            "Apply PLL to a complex numpy array")
        .def(
            "phase_locked_loop_with_stats_array",
            [](const Pll &pll,
               py::array_t<std::complex<float>,
                           py::array::c_style | py::array::forcecast>
                   samples,
               py::array_t<std::complex<float>,
                           py::array::c_style | py::array::forcecast>
                   lut,
               py::object pll_preamble_obj) {
                const py::buffer_info samples_info = samples.request();
                const py::buffer_info lut_info = lut.request();

                auto *samples_ptr =
                    static_cast<std::complex<float> *>(samples_info.ptr);
                auto *lut_ptr =
                    static_cast<std::complex<float> *>(lut_info.ptr);

                std::vector<std::complex<float>> samples_vec(
                    samples_ptr, samples_ptr + samples_info.size);
                std::vector<std::complex<float>> lut_vec(
                    lut_ptr, lut_ptr + lut_info.size);

                std::vector<std::complex<float>> preamble_vec;
                if (!pll_preamble_obj.is_none()) {
                    py::array_t<std::complex<float>,
                                py::array::c_style | py::array::forcecast>
                        preamble_array = pll_preamble_obj.cast<py::array_t<
                            std::complex<float>,
                            py::array::c_style | py::array::forcecast>>();
                    const py::buffer_info preamble_info =
                        preamble_array.request();
                    auto *preamble_ptr =
                        static_cast<std::complex<float> *>(preamble_info.ptr);
                    preamble_vec.assign(preamble_ptr,
                                        preamble_ptr + preamble_info.size);
                }

                std::tuple<std::vector<std::complex<float>>, std::vector<float>,
                           std::vector<float>>
                    out_tuple;
                {
                    py::gil_scoped_release release;
                    out_tuple = pll.phase_lock_with_stats(samples_vec, lut_vec,
                                                          preamble_vec);
                }

                const auto &out_vec = std::get<0>(out_tuple);
                const auto &err_vec = std::get<1>(out_tuple);
                const auto &theta_vec = std::get<2>(out_tuple);

                py::array_t<std::complex<float>> out(samples_info.shape);
                py::buffer_info out_info = out.request();
                auto *out_ptr =
                    static_cast<std::complex<float> *>(out_info.ptr);
                std::copy(out_vec.begin(), out_vec.end(), out_ptr);

                py::array_t<float> error(samples_info.shape);
                py::buffer_info error_info = error.request();
                auto *error_ptr = static_cast<float *>(error_info.ptr);
                std::copy(err_vec.begin(), err_vec.end(), error_ptr);

                py::array_t<float> theta_hist(samples_info.shape);
                py::buffer_info theta_info = theta_hist.request();
                auto *theta_ptr = static_cast<float *>(theta_info.ptr);
                std::copy(theta_vec.begin(), theta_vec.end(), theta_ptr);

                return py::make_tuple(out, error, theta_hist);
            },
            py::arg("samples"), py::arg("lut"),
            py::arg("pll_preamble") = py::none(),
            "Apply PLL and return (derotated, phase_error, theta)");
}

#endif // PYBIND11
