import numpy as np
import ifcopenshell
from math import sqrt
import ifcopenshell.api.root
import ifcopenshell.api.unit
import ifcopenshell.api.context
import ifcopenshell.api.geometry


from .filter_functions import filter_furnishment, filter_low_volume_elements
from .handle_file import beam_and_columns


class GeometricSpace:
    def __init__(self, elements):
        self.elements = elements

    def find_close_elements(self, element, min_dist=1):
        ret = []
        for another in self.elements:
            if another.id == element.id:
                continue  # Don't compare to itself
            if element.find_min_vertice_dis(another) <= min_dist:
                ret.append(another)
        return ret

class Element:
    def __init__(self, id, vertices):
        self.id = id
        self.vertices = vertices
        assert len(self.vertices) > 1  # Ensure there are enough vertices

    def find_specific_min_vertice_dis(self, vertice):
        return min(v.distance_to(vertice) for v in self.vertices)

    def find_min_vertice_dis(self, another):
        return min(self.find_specific_min_vertice_dis(v) for v in another.vertices)

    def find_vertices_to_highlight(self, another_element, min_dist=1):
        ret = []
        for vertice in self.vertices:
            min_distance = another_element.find_specific_min_vertice_dis(vertice)
            if min_distance <= min_dist:
                ret.append(vertice)
        return ret

class Vertice:
    def __init__(self, x, y, z):
        self.x, self.y, self.z = x, y, z

    def distance_to(self, another):
        return sqrt(
            (self.x - another.x) ** 2 +
            (self.y - another.y) ** 2 +
            (self.z - another.z) ** 2
        )

def remove_too_close_ones(vertices, distance_too_close):
    okays = []
    for v in vertices:
        if all(v.distance_to(u) > distance_too_close for u in okays):
            okays.append(v)
    return okays

def find_vertices_and_intersections(beams, columns, distance=1, distance_too_close=0.1):
    beam_elements = [
        Element(id, [Vertice(x, y, z) for x, y, z in vertices])
        for id, vertices in beams.items()
    ]
    column_elements = [
        Element(id, [Vertice(x, y, z) for x, y, z in vertices])
        for id, vertices in columns.items()
    ]

    element_pairs = set()
    vertices_to_highlight = []

    for beam in beam_elements:
        for column in column_elements:
            if beam.find_min_vertice_dis(column) <= distance:
                pair = (beam.id, column.id)
                element_pairs.add(pair)
                # Collect vertices to highlight
                to_highlight = beam.find_vertices_to_highlight(column, distance)
                vertices_to_highlight.extend(to_highlight)

    # Remove too close vertices if necessary
    vertices_to_highlight = remove_too_close_ones(vertices_to_highlight, distance_too_close)

    # Debugging statement
    print(f"Total vertices to highlight: {len(vertices_to_highlight)}")

    return vertices_to_highlight, element_pairs

def mark_vertices(model, vertices_to_mark, output_file_name):
    building_storey = model.by_type("IfcBuildingStorey")[0]
    model3d = ifcopenshell.api.context.add_context(model, context_type="Model")
    body = ifcopenshell.api.context.add_context(
        model, context_type="Model", context_identifier="Body", target_view="MODEL_VIEW", parent=model3d
    )

    # Define the geometry of the marker (e.g., a pyramid)
    vertices = [[(0.0, 0.0, 2.5), (0.0, 0.6, 2.5), (0.6, 0.6, 2.5), (0.6, 0.0, 2.5), (0.3, 0.3, 0.0)]]
    faces = [[(0, 1, 2, 3), (0, 4, 1), (1, 4, 2), (2, 4, 3), (3, 4, 0)]]

    representation = ifcopenshell.api.geometry.add_mesh_representation(
        model, context=body, vertices=vertices, faces=faces
    )

    for vertice in vertices_to_mark:
        matrix = np.eye(4)
        matrix[0, 3] = vertice.x
        matrix[1, 3] = vertice.y
        matrix[2, 3] = vertice.z

        element = ifcopenshell.api.root.create_entity(
            model, ifc_class="IfcElementAssembly", name="Marker"
        )
        ifcopenshell.api.run(
            "spatial.assign_container",
            model,
            products=[element],
            relating_structure=building_storey,
        )
        ifcopenshell.api.geometry.edit_object_placement(
            model, product=element, matrix=matrix
        )
        ifcopenshell.api.geometry.assign_representation(
            model, product=element, representation=representation
        )

    model.write(output_file_name)