/*
Purpose: Orchestrate fetching and enrichment of flight data for display.
Flow:
1) Use BaseStateVectorFetcher to fetch nearby state vectors by geo filter.
2) For each callsign, use BaseFlightFetcher (e.g., AeroAPI) to retrieve FlightInfo.
3) Enrich names via FlightWallFetcher (airline/aircraft display names).
Output: Returns count of enriched flights and fills outStates/outFlights.
*/
#include "core/FlightDataFetcher.h"
#include "config/UserConfiguration.h"
#include "adapters/FlightWallFetcher.h"

FlightDataFetcher::FlightDataFetcher(BaseStateVectorFetcher *stateFetcher,
                                     BaseFlightFetcher *flightFetcher)
    : _stateFetcher(stateFetcher), _flightFetcher(flightFetcher) {}

size_t FlightDataFetcher::fetchFlights(std::vector<StateVector> &outStates,
                                       std::vector<FlightInfo> &outFlights)
{
    outStates.clear();
    outFlights.clear();

    bool ok = _stateFetcher->fetchStateVectors(
        UserConfiguration::CENTER_LAT,
        UserConfiguration::CENTER_LON,
        UserConfiguration::RADIUS_KM,
        outStates);
    if (!ok)
        return 0;

    size_t enriched = 0;
    for (const StateVector &s : outStates)
    {
        if (s.callsign.length() == 0)
        {
            continue;
        }
        FlightInfo info;
        if (_flightFetcher->fetchFlightInfo(s.callsign, info))
        {
            FlightWallFetcher fw;
            if (s.icao24.length())
            {
                String registration;
                String operatorName;
                String operatorIcao;
                String aircraftModel;
                String aircraftType;
                String source;
                String updatedAt;
                bool found = false;
                if (fw.getAircraftEnrichmentByAdsbIcao(s.icao24,
                                                       registration,
                                                       operatorName,
                                                       operatorIcao,
                                                       aircraftModel,
                                                       aircraftType,
                                                       source,
                                                       updatedAt,
                                                       found) &&
                    found)
                {
                    if (registration.length())
                    {
                        info.registration = registration;
                    }
                    if (operatorName.length())
                    {
                        info.airline_display_name_full = operatorName;
                    }
                    if (operatorIcao.length())
                    {
                        info.operator_icao = operatorIcao;
                    }
                    if (aircraftModel.length())
                    {
                        info.aircraft_display_name_short = aircraftModel;
                        info.aircraft_display_name_full = aircraftModel;
                    }
                    if (aircraftType.length())
                    {
                        info.aircraft_code = aircraftType;
                    }
                    info.enrichment_source = source;
                    info.enrichment_updated_at = updatedAt;
                }
            }

            if (info.operator_icao.length())
            {
                String airlineFull;
                if (info.airline_display_name_full.length() == 0 &&
                    fw.getAirlineName(info.operator_icao, airlineFull))
                {
                    info.airline_display_name_full = airlineFull;
                }
            }
            if (info.aircraft_code.length() && info.aircraft_display_name_short.length() == 0)
            {
                String aircraftShort, aircraftFull;
                if (fw.getAircraftName(info.aircraft_code, aircraftShort, aircraftFull))
                {
                    if (aircraftShort.length())
                    {
                        info.aircraft_display_name_short = aircraftShort;
                    }
                    if (aircraftFull.length())
                    {
                        info.aircraft_display_name_full = aircraftFull;
                    }
                }
            }
            outFlights.push_back(info);
            enriched++;
        }
    }
    return enriched;
}
