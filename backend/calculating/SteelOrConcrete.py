import ifcopenshell



# steelOrConcrete.py

def material_identifier(id1, id2, ifcFile):
    mat1 = get_element_material(id1, ifcFile)
    mat2 = get_element_material(id2, ifcFile)
    return mat1, mat2

def get_element_material(element_id, ifcFile):
    element = ifcFile.by_id(element_id)
    material_relations = [rel for rel in getattr(element, 'HasAssociations', []) if rel.is_a("IfcRelAssociatesMaterial")]
    if material_relations:
        material = material_relations[0].RelatingMaterial
        if material.is_a("IfcMaterial"):
            material_name = material.Name.lower()
            if "concrete" in material_name:
                return "concrete"
            elif "steel" in material_name:
                return "steel"
    return "other"
    
