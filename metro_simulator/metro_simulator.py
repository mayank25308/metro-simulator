
import heapq
from collections import defaultdict

INTERCHANGE_TIME = 5  # minutes penalty for switching lines at an interchange


# ---------------------------------------------------------------------------
# 1. Load data from file
# ---------------------------------------------------------------------------
def load_data(filename="metro_data.txt"):
    """
    Reads the metro_data.txt file and returns a list of connections:
        (line_name, station1, station2, travel_time_minutes)
    """
    connections = []
    with open(filename, "r") as f:
        for raw_line in f:
            raw_line = raw_line.strip()
            if not raw_line:
                continue

            parts = raw_line.split(",")
            if len(parts) != 5:
                continue

            line_name, station1, station2, travel_time, _ = (p.strip() for p in parts)

            if not travel_time.isdigit():
                continue

            connections.append((line_name, station1, station2, int(travel_time)))

    return connections


# ---------------------------------------------------------------------------
# 2. Build the graph: nodes are (station, line) pairs
# ---------------------------------------------------------------------------
def build_graph(connections):
    """
    Returns:
        graph: dict mapping (station, line) -> list of ((station, line), weight)
        station_lines: dict mapping station_name -> set of lines serving it
    """
    graph = defaultdict(list)
    station_lines = defaultdict(set)

    # Travel edges along each line
    for line_name, station1, station2, travel_time in connections:
        station_lines[station1].add(line_name)
        station_lines[station2].add(line_name)

        node_a = (station1, line_name)
        node_b = (station2, line_name)
        graph[node_a].append((node_b, travel_time))
        graph[node_b].append((node_a, travel_time))

    # Interchange edges: same station, different lines
    for station, lines in station_lines.items():
        lines = list(lines)
        for i in range(len(lines)):
            for j in range(i + 1, len(lines)):
                node_a = (station, lines[i])
                node_b = (station, lines[j])
                graph[node_a].append((node_b, INTERCHANGE_TIME))
                graph[node_b].append((node_a, INTERCHANGE_TIME))

    return graph, station_lines


# ---------------------------------------------------------------------------
# 3. Dijkstra's algorithm
# ---------------------------------------------------------------------------
def find_fastest_route(graph, station_lines, start, end):
    """
    Returns (total_time, path, error):
        total_time : int, total minutes (including interchange penalties)
        path       : list of (station, line) nodes, in travel order
        error      : str message if something went wrong, else None
    """
    if start not in station_lines:
        return None, None, f"Station '{start}' not found in the network."
    if end not in station_lines:
        return None, None, f"Station '{end}' not found in the network."

    if start == end:
        return 0, [(start, next(iter(station_lines[start])))], None

    dist = defaultdict(lambda: float("inf"))
    prev = {}
    pq = []

    for line in station_lines[start]:
        node = (start, line)
        dist[node] = 0
        heapq.heappush(pq, (0, node))

    visited = set()
    target_lines = station_lines[end]

    while pq:
        d, node = heapq.heappop(pq)
        if node in visited:
            continue
        visited.add(node)

        if node[0] == end and node[1] in target_lines:
            break

        for neighbour, weight in graph[node]:
            nd = d + weight
            if nd < dist[neighbour]:
                dist[neighbour] = nd
                prev[neighbour] = node
                heapq.heappush(pq, (nd, neighbour))

    # Pick the best-reached node at the destination station
    best_node, best_dist = None, float("inf")
    for line in target_lines:
        node = (end, line)
        if dist[node] < best_dist:
            best_dist = dist[node]
            best_node = node

    if best_node is None or best_dist == float("inf"):
        return None, None, "No route found between these stations."

    # Reconstruct path
    path = [best_node]
    node = best_node
    while node in prev:
        node = prev[node]
        path.append(node)
    path.reverse()

    return best_dist, path, None


# ---------------------------------------------------------------------------
def collapse_to_segments(path, graph):
    """
    Converts a list of (station, line) nodes into segments of continuous
    travel on a single line:
        [{"line": "Blue", "stations": [...], "times": [...]}, {"line": "Magenta", ...}]

    "times" holds the travel time (minutes) for each hop within the segment,
    looked up directly from the graph's edge weights.
    """
    segments = []
    for idx, (station, line) in enumerate(path):
        if not segments:
            segments.append({"line": line, "stations": [station], "times": []})
        elif line == segments[-1]["line"]:
            if segments[-1]["stations"][-1] != station:
                prev_node = path[idx - 1]
                hop_time = next(w for n, w in graph[prev_node] if n == (station, line))
                segments[-1]["stations"].append(station)
                segments[-1]["times"].append(hop_time)
        else:
            segments.append({"line": line, "stations": [station], "times": []})
    return segments


# ---------------------------------------------------------------------------
# 5. Train timing helpers (frequency-based schedule)
# ---------------------------------------------------------------------------
def time_to_minutes(time_str):
    h, m = map(int, time_str.split(":"))
    return h * 60 + m


def minutes_to_time(total_minutes):
    h, m = divmod(total_minutes % (24 * 60), 60)
    return f"{h:02d}:{m:02d}"


def get_frequency(minute_of_day):
    """Returns train frequency (minutes between trains) for a given time."""
    hour = minute_of_day // 60
    if (8 <= hour < 10) or (17 <= hour < 19):  # peak hours
        return 4
    return 8


def next_departure(current_minute, freq):
    if current_minute % freq == 0:
        return current_minute
    return current_minute + (freq - current_minute % freq)


# ---------------------------------------------------------------------------
# 6. Output
# ---------------------------------------------------------------------------
def print_route(start, end, total_time, path, graph, start_time=None):
    if start == end:
        print("\nYou're already at your destination!")
        return

    segments = collapse_to_segments(path, graph)
    num_changes = len(segments) - 1

    print("\n" + "=" * 55)
    print(f"  ROUTE: {start}  ->  {end}")
    print("=" * 55)

    clock = time_to_minutes(start_time) if start_time else None

    for idx, seg in enumerate(segments, start=1):
        stations = seg["stations"]
        times = seg["times"]
        num_stops = len(stations) - 1

        print(f"\nStep {idx}: Take the {seg['line']} Line")
        print(f"   {stations[0]}  ->  {stations[-1]}   ({num_stops} stop(s))")

        if clock is not None:
            freq = get_frequency(clock)
            depart = next_departure(clock, freq)
            print(f"   Board train at {minutes_to_time(depart)} "
                  f"(every {freq} min at this time)")
            clock = depart + sum(times)
            print(f"   Arrive at {stations[-1]} by {minutes_to_time(clock)}")

        if idx < len(segments):
            print(f"   -> Change to {segments[idx]['line']} Line at {stations[-1]} "
                  f"(+{INTERCHANGE_TIME} min interchange)")
            if clock is not None:
                clock += INTERCHANGE_TIME

    print("\n" + "-" * 55)
    print(f"Total interchanges : {num_changes}")
    print(f"Total travel time  : {total_time} minutes")
    if start_time:
        print(f"Started at {start_time}, estimated arrival at "
              f"{minutes_to_time(clock)}")
    print("=" * 55 + "\n")


# ---------------------------------------------------------------------------
# 7. CLI
# ---------------------------------------------------------------------------
def get_all_stations(station_lines):
    return sorted(station_lines.keys())


def main():
    connections = load_data("metro_data.txt")
    graph, station_lines = build_graph(connections)

    print("\n" + "#" * 55)
    print("#        DELHI METRO ROUTE SIMULATOR (CLI)            #")
    print("#  Fastest route via Dijkstra's Algorithm             #")
    print("#" * 55)

    while True:
        print("\nOptions:")
        print("  1. Find fastest route between two stations")
        print("  2. List all stations")
        print("  3. Exit")
        choice = input("\nEnter your choice (1/2/3): ").strip()

        if choice == "1":
            start = input("Enter source station: ").strip()
            end = input("Enter destination station: ").strip()
            start_time = input("Enter start time HH:MM (or press Enter to skip): ").strip()
            start_time = start_time if start_time else None

            total_time, path, error = find_fastest_route(graph, station_lines, start, end)

            if error:
                print(f"\n[Error] {error}")
                print("Tip: Use option 2 to see all valid station names.")
                continue

            print_route(start, end, total_time, path, graph, start_time)

        elif choice == "2":
            print("\nAll stations in the network:\n")
            for s in get_all_stations(station_lines):
                print(f"  - {s}")

        elif choice == "3":
            print("\nThanks for using the Delhi Metro Route Simulator. Goodbye!\n")
            break

        else:
            print("\nInvalid choice. Please enter 1, 2, or 3.")


if __name__ == "__main__":
    main()
