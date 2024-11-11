import ifcopenshell


def filter_furnishment(ifc_file):
    remove = []
    furnish = ifc_file.by_type("IfcFurnishingElement")

    for element in furnish:
        ifc_file.remove(element)


def filter_low_volume_elements(ifc_file, volume_threshold=10.0):
    """
    Returns a list of columns and beams that have a Volume property less than the specified threshold.
    
    Args:
        ifc_file_path (str): Path to the IFC file.
        volume_threshold (float): The volume threshold in cubic meters.
        
    Returns:
        List[Tuple[str, float]]: A list of tuples containing the GlobalId and volume of each element 
                                 with a volume below the threshold.
    """
    
    def get_volume_property(element):
        for definition in element.IsDefinedBy:
            if hasattr(definition, "RelatingPropertyDefinition"):
                property_set = definition.RelatingPropertyDefinition
                if property_set.is_a("IfcPropertySet"):
                    for prop in property_set.HasProperties:
                        if prop.Name == "Volume" and prop.NominalValue:
                            return float(prop.NominalValue.wrappedValue)
        return None
    
    for element_type in ["IfcColumn", "IfcBeam"]:
        elements = ifc_file.by_type(element_type)
        
        for element in elements:
            volume = get_volume_property(element)
            
            if volume is not None and volume < volume_threshold:
                ifc_file.remove(element)
