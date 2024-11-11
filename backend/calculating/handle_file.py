import ifcopenshell
import ifcopenshell.geom

# Load the IFC file


# Function to extract vertex coordinates from a shape
def get_vertices(shape):
    vertices = []
    verts = shape.geometry.verts  # Flattened list of vertex coordinates [x1, y1, z1, x2, y2, z2, ...]
    for i in range(0, len(verts), 3):
        x, y, z = verts[i], verts[i+1], verts[i+2]
        vertices.append((x, y, z))
    return vertices

def beam_and_columns(ifc_file):
    # Process each beam and column
    # Set up geometry settings
    settings = ifcopenshell.geom.settings()
    settings.set(settings.USE_WORLD_COORDS, True)

    # Find all beams and columns
    beams = ifc_file.by_type("IfcBeam")
    columns = ifc_file.by_type("IfcColumn")

    beam_vertices = {}
    column_vertices = {}

    for beam in beams:
        shape = ifcopenshell.geom.create_shape(settings, beam)
        beam_vertices[beam.id()] = get_vertices(shape)

    for column in columns:
        shape = ifcopenshell.geom.create_shape(settings, column)
        column_vertices[column.id()] = get_vertices(shape)

    return (beam_vertices, column_vertices)

    


def main():
    file_path = "./data/test.ifc"
    ifc_file = ifcopenshell.open(file_path)
    beam, column = beam_and_columns(ifc_file)

    beams = list(map(lambda x: x.id() ,ifc_file.by_type("IfcBeam")))

    print(len(beam[beams[0]]))



    






if __name__=="__main__":
    main()

