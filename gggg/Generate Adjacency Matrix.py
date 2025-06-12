import os
import csv
from geopy.distance import geodesic
from collections import defaultdict


def load_route_chains(route_chains_file):
    """Loads stop sequences for each route from route_chains.csv."""
    route_chains = {}
    with open(route_chains_file, "r") as f:
        reader = csv.reader(f)
        next(reader)  # Skip header
        for row in reader:
            route = row[0]
            stops = eval(row[1])  # Convert string list to actual list
            route_chains[route] = stops
    return route_chains


def load_route_points(directory):
    """Loads all route points (stops + intermediate points) from CSV files."""
    route_points = {}
    for filename in sorted(os.listdir(directory)):
        if filename.endswith(".csv"):
            file_path = os.path.join(directory, filename)
            points = []
            with open(file_path, "r") as f:
                reader = csv.reader(f)
                next(reader)  # Skip header
                for row in reader:
                    if len(row) == 3:
                        try:
                            point_id, lon, lat = int(row[0]), float(row[1]), float(row[2])
                            points.append((point_id, lon, lat))
                        except ValueError:
                            continue
            route_points[filename] = points
    return route_points


def calculate_distance(point1, point2):
    """Calculates geodesic distance between two points."""
    return geodesic((point1[2], point1[1]), (point2[2], point2[1])).meters


def map_duplicate_stops(route_points):
    """Finds stops with different IDs but identical locations (e.g., 101 & 201)."""
    location_to_stop = {}  # {(lon, lat): stop_id}
    stop_mapping = {}  # {stop_id: canonical_id}

    for points in route_points.values():
        for stop_id, lon, lat in points:
            if stop_id != 0:  # Ignore route points
                key = (lon, lat)
                if key in location_to_stop:
                    stop_mapping[stop_id] = location_to_stop[key]
                else:
                    location_to_stop[key] = stop_id
                    stop_mapping[stop_id] = stop_id

    return stop_mapping


def generate_adjacency_matrix(route_chains, route_points):
    """Generates an adjacency matrix using distances between stops."""
    adjacency_matrix = defaultdict(dict)
    stop_mapping = map_duplicate_stops(route_points)  # Handle duplicate stops

    for route, stops in route_chains.items():
        if route not in route_points:
            continue  # Skip if no file found

        points = route_points[route]
        stop_indices = {stop: i for i, (stop, _, _) in enumerate(points) if stop in stops}
        stop_sequence = sorted(stop_indices.keys(), key=lambda s: stop_indices[s])

        for i in range(len(stop_sequence) - 1):
            stop1 = stop_mapping[stop_sequence[i]]
            stop2 = stop_mapping[stop_sequence[i + 1]]

            # Calculate distance using route points
            idx1, idx2 = stop_indices[stop1], stop_indices[stop2]
            total_distance = sum(calculate_distance(points[j], points[j + 1]) for j in range(idx1, idx2))

            adjacency_matrix[stop1][stop2] = total_distance

    return adjacency_matrix


def save_adjacency_matrix(matrix, output_file="adjacency_matrix.csv"):
    """Saves the adjacency matrix to a CSV file."""
    with open(output_file, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["From", "To", "Distance (meters)"])
        for from_stop, destinations in matrix.items():
            for to_stop, distance in destinations.items():
                writer.writerow([from_stop, to_stop, round(distance, 2)])


# Usage Example
directory_path = "Djikstra Data Set"  # Directory containing route CSV files
route_chains_file = "route_chains.csv"  # CSV file with stop sequences

route_chains = load_route_chains(route_chains_file)
route_points = load_route_points(directory_path)
adjacency_matrix = generate_adjacency_matrix(route_chains, route_points)
save_adjacency_matrix(adjacency_matrix)
