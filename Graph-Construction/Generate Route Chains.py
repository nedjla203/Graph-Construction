import os
import csv
from geopy.distance import geodesic

def load_stops_from_csv(directory_path):
    """Loads all points (stops and route points) from all CSV files in the directory."""
    stops_by_file = {}
    route_chains = {}
    all_stops = []
    all_rows_by_file = {}  # Store all rows (stops + route points)

    for filename in sorted(os.listdir(directory_path)):
        if filename.endswith(".csv"):
            file_path = os.path.join(directory_path, filename)
            stops = []
            stop_ids = []
            all_rows = []

            with open(file_path, "r") as f:
                reader = csv.reader(f)
                header = next(reader)
                all_rows.append(header)  # Save header

                for row in reader:
                    if len(row) == 3:
                        try:
                            stop_id, lon, lat = int(row[0]), float(row[1]), float(row[2])
                            all_rows.append([stop_id, lon, lat])
                            if stop_id != 0:
                                stops.append((stop_id, lon, lat))
                                stop_ids.append(stop_id)
                                all_stops.append((stop_id, lon, lat))
                        except ValueError:
                            continue

            stops_by_file[filename] = stops
            route_chains[filename] = stop_ids
            all_rows_by_file[filename] = all_rows

    return stops_by_file, route_chains, all_stops, all_rows_by_file


def find_root(stop_id, stop_id_map):
    """Finds root stop ID with path compression."""
    path = []
    while stop_id in stop_id_map:
        path.append(stop_id)
        stop_id = stop_id_map[stop_id]
    for node in path:
        stop_id_map[node] = stop_id
    return stop_id


def find_and_merge_nearby_stops(stops_by_file, route_chains, max_distance_meters=5):
    """Finds and merges nearby stops with the smallest stop ID."""
    stop_id_map = {}

    all_stops = []
    for stops in stops_by_file.values():
        all_stops.extend(stops)

    # Compare all pairs of stops
    for i in range(len(all_stops)):
        id1, lon1, lat1 = all_stops[i]
        for j in range(i + 1, len(all_stops)):
            id2, lon2, lat2 = all_stops[j]
            if id1 == id2:
                continue
            distance = geodesic((lat1, lon1), (lat2, lon2)).meters
            if distance <= max_distance_meters:
                root1 = find_root(id1, stop_id_map)
                root2 = find_root(id2, stop_id_map)
                if root1 != root2:
                    min_id = min(root1, root2)
                    max_id = max(root1, root2)
                    stop_id_map[max_id] = min_id

    # Update stops and route chains
    for filename in stops_by_file:
        stops_by_file[filename] = [
            (find_root(stop_id, stop_id_map), lon, lat)
            for stop_id, lon, lat in stops_by_file[filename]
        ]

        # Clean route chains: remove consecutive duplicates after remapping
        updated_chain = []
        previous_stop = None
        for stop_id in route_chains[filename]:
            new_id = find_root(stop_id, stop_id_map)
            if new_id != previous_stop:
                updated_chain.append(new_id)
                previous_stop = new_id
        route_chains[filename] = updated_chain

    return stops_by_file, route_chains, stop_id_map


def save_route_chains(route_chains, output_file="route_chains.csv"):
    """Saves the updated route chains in a summary CSV format."""
    with open(output_file, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Route", "Stop Chain"])
        for route, chain in route_chains.items():
            writer.writerow([route, "[" + ", ".join(map(str, chain)) + "]"])


def save_updated_routes_to_csv(directory_path, stops_by_file, all_rows_by_file, stop_id_map):
    """Overwrites original CSV files with updated stop IDs, preserving route points (ID = 0)."""
    for filename in all_rows_by_file:
        file_path = os.path.join(directory_path, filename)
        with open(file_path, "w", newline="") as f:
            writer = csv.writer(f)
            for row in all_rows_by_file[filename]:
                if row[0] == "id":
                    writer.writerow(row)  # Header
                    continue
                try:
                    stop_id = int(row[0])
                    lon = float(row[1])
                    lat = float(row[2])
                    if stop_id != 0:
                        new_id = find_root(stop_id, stop_id_map)
                        writer.writerow([new_id, lon, lat])
                    else:
                        writer.writerow([0, lon, lat])
                except ValueError:
                    continue


# === Usage Example ===
directory_path = "Djikstra Data Set"  # Change this to your folder

stops_by_file, route_chains, all_stops, all_rows_by_file = load_stops_from_csv(directory_path)

stops_by_file, updated_route_chains, stop_id_map = find_and_merge_nearby_stops(
    stops_by_file, route_chains, max_distance_meters=60
)

save_route_chains(updated_route_chains)
save_updated_routes_to_csv(directory_path, stops_by_file, all_rows_by_file, stop_id_map)
