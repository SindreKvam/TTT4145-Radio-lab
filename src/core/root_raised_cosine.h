
#ifndef ROOT_RAISED_COSINE_H
#define ROOT_RAISED_COSINE_H

#include "fir.h"

class RootRaisedCosine : public Fir {

  public:
    RootRaisedCosine(float beta, int span, int sps);
    ~RootRaisedCosine();
};

#endif // !ROOT_RAISED_COSINE_H
