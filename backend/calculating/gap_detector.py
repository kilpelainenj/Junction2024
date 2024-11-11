"""mport ifcopenshell
import ifcopenshell.geom
from math import sqrt

settings = ifcopenshell.geom.settings()

def EuclideanDistance(point1, point2):
    return sqrt(
        (point1[0] - point2[0]) ** 2
        + (point1[1] - point2[1]) ** 2
        + (point1[2] - point2[2]) ** 2
    )


def get_column_centroid(element):
    shape = ifcopenshell.geom.create_shape(settings, element)
    vertices = shape.geometry.verts

    points = [
        (vertices[i], vertices[i + 1], vertices[i + 2])
        for i in range(0, len(vertices), 3)
    ]
    centroid = [sum(coord) / len(points) for coord in zip(*points)]

    return centroid


def detect_column_gaps(ifc_file_path, gap_threshold):

    ifc_file = ifcopenshell.open(ifc_file_path)

    
    settings.set(settings.USE_PYTHON_OPENCASCADE, True)

    gap_list = []

    columns = ifc_file.by_type("IfcColumn")

    column_centroids = {column: get_column_centroid(column) for column in columns}

    for i, column1 in enumerate(columns):
        for j, column2 in enumerate(columns):
            if i >= j:
                continue

            centroid1 = column_centroids[column1]
            centroid2 = column_centroids[column2]
            distance = calculate_distance(centroid1, centroid2)

            if distance > gap_threshold:
                gap_list.append((column1.GlobalId, column2.GlobalId, distance))

    return gap_list
    """
