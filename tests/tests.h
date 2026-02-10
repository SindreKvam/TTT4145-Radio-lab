#pragma once

#include <matplot/matplot.h>

#define MATPLOT_GENERAL_FONT_SIZE 18
#define MATPLOT_LABEL_SIZE 16

matplot::figure_handle generate_figure() {

    matplot::figure_handle fig = matplot::figure(true);
    auto ax = matplot::gca();

    // Set font sizes etc
    ax->font_size(MATPLOT_GENERAL_FONT_SIZE);
    ax->title_font_size_multiplier(1.2);
    ax->x_axis().label_font_size(MATPLOT_LABEL_SIZE);
    ax->y_axis().label_font_size(MATPLOT_LABEL_SIZE);
    ax->position(
        {0.15, 0.15, 0.75, 0.70}); // Title gets removed if we dont do this

    return fig;
}
