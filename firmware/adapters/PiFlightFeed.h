#pragma once
#include <vector>
#include "models/FlightInfo.h"

class PiFlightFeed
{
public:
    enum class Status { Unavailable, Stale, Ok };
    bool fetchFlights(std::vector<FlightInfo> &flights);
    Status status() const { return _status; }
private:
    Status _status = Status::Unavailable;
};
