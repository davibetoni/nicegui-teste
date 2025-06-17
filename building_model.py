import trimesh
import numpy as np
import os
import time
import sys
import traceback

def generate_with(material_type='wood', num_floors=3):
    """
    Gera um modelo GLB de uma estrutura de prédio com a quantidade de andares especificada.
    A aparência varia com o material (wood/steel/concrete).
    """
    try:
        num_floors = max(1, int(num_floors)) 

        # Dimensões base para a estrutura
        floor_width = 4.0   # Largura total do andar
        floor_depth = 4.0   # Profundidade total do andar
        floor_slab_height = 0.2 # Espessura da laje
        
        column_dim = 0.3 # Dimensão quadrada do pilar (0.3x0.3)
        beam_height = 0.3 # Altura da viga (mesma dimensão do pilar)
        beam_width = 0.3  # Largura da viga (mesma dimensão do pilar)
        
        # Altura livre entre as lajes
        story_height = 3.0 # Altura de um andar (pilar + viga + espaço livre)

        meshes = []

        # --- Iterar sobre os andares ---
        for i in range(num_floors):
            floor_z_bottom = i * story_height # Base Z para o andar atual
            
            # 1. Lajes (se necessário, para simular o piso)
            # A laje pode ser mais fina ou apenas um placeholder visual
            # Se você quer a estrutura bem aberta, pode remover a laje
            floor_slab = trimesh.creation.box(extents=[floor_width, floor_depth, floor_slab_height])
            floor_slab.apply_translation([0, 0, floor_z_bottom + floor_slab_height / 2])
            meshes.append(floor_slab)

            # 2. Pilares para o andar atual
            # Posicionamento dos 4 pilares nos cantos
            column_x_offset = floor_width / 2 - column_dim / 2
            column_y_offset = floor_depth / 2 - column_dim / 2
            
            column_positions = [
                np.array([ column_x_offset,  column_y_offset, floor_z_bottom + floor_slab_height]),
                np.array([-column_x_offset,  column_y_offset, floor_z_bottom + floor_slab_height]),
                np.array([ column_x_offset, -column_y_offset, floor_z_bottom + floor_slab_height]),
                np.array([-column_x_offset, -column_y_offset, floor_z_bottom + floor_slab_height]),
            ]

            for pos in column_positions:
                # Altura do pilar é story_height - floor_slab_height (espaço entre lajes)
                pillar = trimesh.creation.box(extents=[column_dim, column_dim, story_height - floor_slab_height])
                pillar.apply_translation([pos[0], pos[1], pos[2] + (story_height - floor_slab_height) / 2])
                meshes.append(pillar)

            # 3. Vigas para o andar atual (no topo dos pilares, embaixo da próxima laje)
            # Se for o último andar, não haverá vigas "acima" dele, a menos que queira um telhado.
            # Aqui, as vigas conectam os pilares e formam um quadro no topo de cada andar.
            if i < num_floors: # Adiciona vigas acima deste andar
                beam_z = floor_z_bottom + story_height - beam_height / 2

                # Vigas nas direções X (front-back)
                beam_length_x = floor_width - column_dim
                beam_x1 = trimesh.creation.box(extents=[beam_length_x, beam_width, beam_height])
                beam_x1.apply_translation([0, column_y_offset, beam_z])
                meshes.append(beam_x1)

                beam_x2 = trimesh.creation.box(extents=[beam_length_x, beam_width, beam_height])
                beam_x2.apply_translation([0, -column_y_offset, beam_z])
                meshes.append(beam_x2)

                # Vigas nas direções Y (left-right)
                beam_length_y = floor_depth - column_dim
                beam_y1 = trimesh.creation.box(extents=[beam_width, beam_length_y, beam_height])
                beam_y1.apply_translation([column_x_offset, 0, beam_z])
                meshes.append(beam_y1)

                beam_y2 = trimesh.creation.box(extents=[beam_width, beam_length_y, beam_height])
                beam_y2.apply_translation([-column_x_offset, 0, beam_z])
                meshes.append(beam_y2)

        # Combinar todas as geometrias
        combined = trimesh.util.concatenate(meshes)

        pbr_material_instance = None 

        # Definir material com base no tipo
        if material_type == 'wood':
            base_color = [0.6, 0.4, 0.2, 1.0] # Marrom para madeira
            pbr_material_instance = trimesh.visual.texture.PBRMaterial(
                baseColorFactor=base_color,
                metallicFactor=0.0,      # Não metálico
                roughnessFactor=0.8,     # Áspero
                emissiveFactor=[0,0,0]
            )
        elif material_type == 'steel':
            base_color = [0.7, 0.7, 0.7, 1.0] # Cinza para aço
            pbr_material_instance = trimesh.visual.texture.PBRMaterial(
                baseColorFactor=base_color,
                metallicFactor=0.9,      # Muito metálico
                roughnessFactor=0.3,     # Mais liso/reflexivo
                emissiveFactor=[0,0,0]
            )
        elif material_type == 'concrete': # NOVO MATERIAL: Concreto
            base_color = [0.55, 0.55, 0.55, 1.0] # Um cinza médio para concreto
            pbr_material_instance = trimesh.visual.texture.PBRMaterial(
                baseColorFactor=base_color,
                metallicFactor=0.05,     # Levemente metálico (quase nada)
                roughnessFactor=0.9,     # Muito áspero (como concreto)
                emissiveFactor=[0,0,0]
            )
        else:
            base_color = [0.5, 0.5, 0.5, 1.0]
            pbr_material_instance = trimesh.visual.texture.PBRMaterial(
                baseColorFactor=base_color,
                metallicFactor=0.5,
                roughnessFactor=0.5,
                emissiveFactor=[0,0,0]
            )

        combined.visual = trimesh.visual.TextureVisuals()
        combined.visual.material = pbr_material_instance

        filename = f"building_{material_type}_{num_floors}_floors_{int(time.time())}.glb"
        filepath = os.path.join("static", filename)

        combined.export(filepath)

        return filepath
    except Exception as e:
        sys.stderr.write(f"Erro ao gerar modelo GLB: {e}\n")
        traceback.print_exc(file=sys.stderr)
        return None

if __name__ == '__main__':
    print(f"Modelo de madeira (2 andares) gerado em: {generate_with('wood', 2)}")
    print(f"Modelo de aço (5 andares) gerado em: {generate_with('steel', 5)}")
    print(f"Modelo de concreto (3 andares) gerado em: {generate_with('concrete', 3)}")