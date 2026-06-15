
Delhi Metro Route Simulator
----------------------------
Reads metro line data from metro_data.txt and finds the FASTEST route
between two stations using Dijkstra's algorithm.

metro_data.txt format (one connection per line):
    LineName,Station1,Station2,TravelTimeInMinutes,IsInterchangeStation(Yes/No)

Each (station, line) combination is treated as a separate node in the graph.
This lets us:
  - Travel along a line via normal edges (weight = travel time)
  - Switch lines at an interchange station via an "interchange edge"
    (weight = INTERCHANGE_TIME)

Dijkstra's algorithm then finds the minimum-time path, naturally accounting
for both travel time AND the cost of changing lines.

