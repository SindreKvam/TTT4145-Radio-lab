#pragma once

#include "fir.h"

class RootRaisedCosine : public Fir {

  public:
    RootRaisedCosine(float beta, int span, int sps);
    ~RootRaisedCosine();
};
