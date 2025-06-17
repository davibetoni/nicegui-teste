# building_model.py
import trimesh
import numpy as np
import os
import time
import sys
import traceback
import io # Import io for handling bytes in memory

def generate_with(material_type='wood', num_floors=1, return_bytes=False):
    """
    Generates a GLB model of a building structure with the specified number of floors.
    Appearance varies with material (wood/steel/concrete).
    If return_bytes is True, returns the GLB bytes; otherwise, saves to a file.
    """
    try:
        num_floors = max(1, int(num_floors)) 

        # Dimensions for the structure (you can adjust these as needed)
        floor_width = 4.0   
        floor_depth = 4.0   
        floor_slab_height = 0.2 
        column_dim = 0.3 
        beam_height = 0.3 
        beam_width = 0.3  
        story_height = 3.0 

        meshes = []

        for i in range(num_floors):
            floor_z_bottom = i * story_height 
            
            # Floor Slab
            floor_slab = trimesh.creation.box(extents=[floor_width, floor_depth, floor_slab_height])
            floor_slab.apply_translation([0, 0, floor_z_bottom + floor_slab_height / 2])
            meshes.append(floor_slab)

            # Columns
            column_x_offset = floor_width / 2 - column_dim / 2
            column_y_offset = floor_depth / 2 - column_dim / 2
            
            column_positions = [
                np.array([ column_x_offset,  column_y_offset, floor_z_bottom + floor_slab_height]),
                np.array([-column_x_offset,  column_y_offset, floor_z_bottom + floor_slab_height]),
                np.array([ column_x_offset, -column_y_offset, floor_z_bottom + floor_slab_height]),
                np.array([-column_x_offset, -column_y_offset, floor_z_bottom + floor_slab_height]),
            ]

            for pos in column_positions:
                pillar = trimesh.creation.box(extents=[column_dim, column_dim, story_height - floor_slab_height])
                pillar.apply_translation([pos[0], pos[1], pos[2] + (story_height - floor_slab_height) / 2])
                meshes.append(pillar)

            # Beams (connecting columns at the top of each floor)
            if i < num_floors: 
                beam_z = floor_z_bottom + story_height - beam_height / 2

                beam_length_x = floor_width - column_dim
                beam_x1 = trimesh.creation.box(extents=[beam_length_x, beam_width, beam_height])
                beam_x1.apply_translation([0, column_y_offset, beam_z])
                meshes.append(beam_x1)

                beam_x2 = trimesh.creation.box(extents=[beam_length_x, beam_width, beam_height])
                beam_x2.apply_translation([0, -column_y_offset, beam_z])
                meshes.append(beam_x2)

                beam_length_y = floor_depth - column_dim
                beam_y1 = trimesh.creation.box(extents=[beam_width, beam_length_y, beam_height])
                beam_y1.apply_translation([column_x_offset, 0, beam_z])
                meshes.append(beam_y1)

                beam_y2 = trimesh.creation.box(extents=[beam_width, beam_length_y, beam_height])
                beam_y2.apply_translation([-column_x_offset, 0, beam_z])
                meshes.append(beam_y2)
        
        combined = trimesh.util.concatenate(meshes)

        pbr_material_instance = None 

        # Define material based on type
        if material_type == 'wood':
            base_color = [0.6, 0.4, 0.2, 1.0]
            pbr_material_instance = trimesh.visual.texture.PBRMaterial(
                baseColorFactor=base_color, metallicFactor=0.0, roughnessFactor=0.8, emissiveFactor=[0,0,0])
        elif material_type == 'steel':
            base_color = [0.7, 0.7, 0.7, 1.0]
            pbr_material_instance = trimesh.visual.texture.PBRMaterial(
                baseColorFactor=base_color, metallicFactor=0.9, roughnessFactor=0.3, emissiveFactor=[0,0,0])
        elif material_type == 'concrete':
            base_color = [0.55, 0.55, 0.55, 1.0]
            pbr_material_instance = trimesh.visual.texture.PBRMaterial(
                baseColorFactor=base_color, metallicFactor=0.05, roughnessFactor=0.9, emissiveFactor=[0,0,0])
        else:
            base_color = [0.5, 0.5, 0.5, 1.0]
            pbr_material_instance = trimesh.visual.texture.PBRMaterial(
                baseColorFactor=base_color, metallicFactor=0.5, roughnessFactor=0.5, emissiveFactor=[0,0,0])

        combined.visual = trimesh.visual.TextureVisuals()
        combined.visual.material = pbr_material_instance

        # --- NEW LOGIC: Return bytes or save to file ---
        if return_bytes:
            buffer = io.BytesIO()
            combined.export(buffer, file_type='glb')
            buffer.seek(0)
            return buffer.read()
        else:
            filename = f"building_{material_type}_{num_floors}_floors_{int(time.time())}.glb"
            filepath = os.path.join("static", filename)
            combined.export(filepath)
            return filepath
    except Exception as e:
        sys.stderr.write(f"Error generating GLB model: {e}\n")
        traceback.print_exc(file=sys.stderr)
        return None

if __name__ == '__main__':
    # Test byte generation
    wood_bytes = generate_with('wood', 2, return_bytes=True)
    if wood_bytes:
        print(f"Wood model (2 floors) generated in memory, size: {len(wood_bytes)} bytes")
    
    # Test file saving (old way)
    # print(f"Steel model (5 floors) generated to file: {generate_with('steel', 5)}")