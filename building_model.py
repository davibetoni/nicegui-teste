import trimesh
import numpy as np
import os
import time
import sys
import traceback
import io # Import io for handling bytes in memory

def generate_with(material_type='wood', num_floors=1, floor_slab_thickness_param=0.2, return_bytes=False):
    """
    Gera um modelo GLB de uma estrutura de prédio com a quantidade de andares especificada.
    A aparência varia com o material (wood/steel/concrete) e a espessura da laje.
    
    Parameters:
    - material_type (str): Type of material ('wood', 'steel', 'concrete').
    - num_floors (int): Number of floors for the building.
    - floor_slab_thickness_param (float): Desired thickness of the floor slabs in meters.
    - return_bytes (bool): If True, returns the GLB bytes directly. If False, saves to a file (legacy).

    Returns:
    - bytes: The GLB file content as bytes if `return_bytes` is True.
    - str: The filepath of the saved GLB file if `return_bytes` is False.
    - None: If an error occurs during generation.
    """
    try:
        num_floors = max(1, int(num_floors)) # Ensure at least 1 floor
        # Use the provided thickness parameter, ensuring it's a float and has a reasonable minimum value
        floor_slab_height = max(0.05, float(floor_slab_thickness_param)) 
        
        # --- Building Dimensions ---
        # Define core dimensions of a single story and structural elements
        floor_width = 4.0   # Width of the building floor
        floor_depth = 4.0   # Depth of the building floor
        column_dim = 0.3    # Side length of square columns
        beam_height = 0.3   # Height of beams
        beam_width = 0.3    # Width of beams
        story_height = 3.0  # Total height of one story (from floor to floor above)

        # Calculate pillar height based on total story height and slab thickness
        pillar_height = story_height - floor_slab_height

        meshes = [] # List to store all individual Trimesh objects

        # --- Generate Floors and Columns ---
        for i in range(num_floors):
            # Z-coordinate for the bottom of the current floor's structure
            floor_z_bottom = i * story_height 
            
            # 1. Floor Slab
            floor_slab = trimesh.creation.box(extents=[floor_width, floor_depth, floor_slab_height])
            # Position the slab correctly: center it horizontally, and place its bottom at floor_z_bottom
            floor_slab.apply_translation([0, 0, floor_z_bottom + floor_slab_height / 2])
            meshes.append(floor_slab)

            # 2. Columns (Pillars)
            # Calculate offsets for columns to be at the corners of the floor
            column_x_offset = floor_width / 2 - column_dim / 2
            column_y_offset = floor_depth / 2 - column_dim / 2
            
            # Define positions for the four corner columns
            column_positions = [
                np.array([ column_x_offset,  column_y_offset, floor_z_bottom + floor_slab_height]),
                np.array([-column_x_offset,  column_y_offset, floor_z_bottom + floor_slab_height]),
                np.array([ column_x_offset, -column_y_offset, floor_z_bottom + floor_slab_height]),
                np.array([-column_x_offset, -column_y_offset, floor_z_bottom + floor_slab_height]),
            ]

            # Create and position each column
            for pos in column_positions:
                pillar = trimesh.creation.box(extents=[column_dim, column_dim, pillar_height]) 
                # Position the pillar: its bottom starts where the slab ends
                pillar.apply_translation([pos[0], pos[1], pos[2] + pillar_height / 2])
                meshes.append(pillar)

            # 3. Beams (connecting columns at the top of each floor)
            # Beams are added for each floor, except possibly the very top if no more floors are above.
            # In this logic, beams are created for each floor's "ceiling"
            if i < num_floors: # This condition might be simplified or removed depending on exact beam placement
                # Z-coordinate for the center of the beams
                # It's at the top of the current story
                beam_z = floor_z_bottom + story_height - beam_height / 2

                # Beams along X-axis
                beam_length_x = floor_width - column_dim # Length between columns
                beam_x1 = trimesh.creation.box(extents=[beam_length_x, beam_width, beam_height])
                beam_x1.apply_translation([0, column_y_offset, beam_z])
                meshes.append(beam_x1)

                beam_x2 = trimesh.creation.box(extents=[beam_length_x, beam_width, beam_height])
                beam_x2.apply_translation([0, -column_y_offset, beam_z])
                meshes.append(beam_x2)

                # Beams along Y-axis
                beam_length_y = floor_depth - column_dim # Length between columns
                beam_y1 = trimesh.creation.box(extents=[beam_width, beam_length_y, beam_height])
                beam_y1.apply_translation([column_x_offset, 0, beam_z])
                meshes.append(beam_y1)

                beam_y2 = trimesh.creation.box(extents=[beam_width, beam_length_y, beam_height])
                beam_y2.apply_translation([-column_x_offset, 0, beam_z])
                meshes.append(beam_y2)
        
        # Combine all individual meshes into a single Trimesh object
        combined = trimesh.util.concatenate(meshes)

        # --- Apply Material Properties (PBR Material) ---
        pbr_material_instance = None 

        if material_type == 'wood':
            base_color = [0.6, 0.4, 0.2, 1.0] # RGBa for wood-like color
            pbr_material_instance = trimesh.visual.texture.PBRMaterial(
                baseColorFactor=base_color, metallicFactor=0.0, roughnessFactor=0.8, emissiveFactor=[0,0,0])
        elif material_type == 'steel':
            base_color = [0.7, 0.7, 0.7, 1.0] # RGBa for steel-like color
            pbr_material_instance = trimesh.visual.texture.PBRMaterial(
                baseColorFactor=base_color, metallicFactor=0.9, roughnessFactor=0.3, emissiveFactor=[0,0,0])
        elif material_type == 'concrete':
            base_color = [0.55, 0.55, 0.55, 1.0] # RGBa for concrete-like color
            pbr_material_instance = trimesh.visual.texture.PBRMaterial(
                baseColorFactor=base_color, metallicFactor=0.05, roughnessFactor=0.9, emissiveFactor=[0,0,0])
        else:
            # Default material if type is not recognized
            base_color = [0.5, 0.5, 0.5, 1.0] 
            pbr_material_instance = trimesh.visual.texture.PBRMaterial(
                baseColorFactor=base_color, metallicFactor=0.5, roughnessFactor=0.5, emissiveFactor=[0,0,0])

        combined.visual = trimesh.visual.TextureVisuals()
        combined.visual.material = pbr_material_instance

        # --- Export Model ---
        if return_bytes:
            # Export to a BytesIO buffer in memory and return its content
            buffer = io.BytesIO()
            combined.export(buffer, file_type='glb')
            buffer.seek(0) # Rewind the buffer to the beginning
            return buffer.read() # Return the bytes
        else:
            # Legacy: Save to a file in the 'static' directory (not used in multi-user setup)
            filename = f"building_{material_type}_{num_floors}_floors_{int(time.time())}.glb"
            filepath = os.path.join("static", filename)
            combined.export(filepath)
            return filepath
            
    except Exception as e:
        # Log any errors that occur during model generation
        sys.stderr.write(f"Error generating GLB model: {e}\n")
        traceback.print_exc(file=sys.stderr) # Print full traceback for detailed debugging
        return None

# --- Main execution block (for direct testing of building_model.py) ---
if __name__ == '__main__':
    print("--- Testing building_model.py directly ---")
    
    # Test generating a model as bytes with a specific thickness
    test_thickness = 0.25 # meters
    test_wood_bytes = generate_with('wood', 3, test_thickness, return_bytes=True)
    if test_wood_bytes:
        print(f"Wood model (3 floors, {test_thickness}m thickness) generated in memory, size: {len(test_wood_bytes)} bytes.")
        # Optional: Save to a temporary file to verify the output
        # with open("test_wood_model.glb", "wb") as f:
        #     f.write(test_wood_bytes)
        # print("Saved test_wood_model.glb for inspection.")
    else:
        print("Failed to generate test wood model.")
    
    # Test generating a model as a file (legacy mode)
    test_steel_filepath = generate_with('steel', 5, 0.15, return_bytes=False)
    if test_steel_filepath:
        print(f"Steel model (5 floors, 0.15m thickness) generated to file: {test_steel_filepath}")
    else:
        print("Failed to generate test steel model to file.")