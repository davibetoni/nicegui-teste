from nicegui import ui, app
from fastapi.responses import Response
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import math
import io
import base64
import uuid
import time
import trimesh

# Global configurations
arquivo = 'Database.xlsx'
lista_resultados = []
lista_dicionarios = []

# Dictionary to store images in memory
in_memory_images = {}
in_memory_models = {}

# Global UI component variables
resultado_text = None
resultado_grafico_html = None
model_viewer_html_element = None # Renamed for clarity: this will be the ui.html component that holds the model-viewer
tabs = None

# Generate initial default model
initial_model_bytes = None
initial_model_id = None

# generate_with function
def generate_with(material_type='wood', num_floors=1, floor_slab_thickness_param=0.2, return_bytes=False):
    try:
        num_floors = max(1, int(num_floors))
        floor_slab_height = max(0.05, float(floor_slab_thickness_param))
        
        floor_width = 4.0
        floor_depth = 4.0
        column_dim = 0.3
        beam_height = 0.3
        beam_width = 0.3
        story_height = 3.0
        pillar_height = story_height - floor_slab_height

        meshes = []

        for i in range(num_floors):
            floor_z_bottom = i * story_height
            
            # Slab
            floor_slab = trimesh.creation.box(extents=[floor_width, floor_depth, floor_slab_height])
            floor_slab.apply_translation([0, 0, floor_z_bottom + floor_slab_height / 2])
            meshes.append(floor_slab)

            # Pillars
            column_x_offset = floor_width / 2 - column_dim / 2
            column_y_offset = floor_depth / 2 - column_dim / 2
            
            column_positions = [
                [column_x_offset, column_y_offset, floor_z_bottom + floor_slab_height],
                [-column_x_offset, column_y_offset, floor_z_bottom + floor_slab_height],
                [column_x_offset, -column_y_offset, floor_z_bottom + floor_slab_height],
                [-column_x_offset, -column_y_offset, floor_z_bottom + floor_slab_height],
            ]

            for pos in column_positions:
                pillar = trimesh.creation.box(extents=[column_dim, column_dim, pillar_height])
                pillar.apply_translation([pos[0], pos[1], pos[2] + pillar_height / 2])
                meshes.append(pillar)

            # Beams
            beam_z = floor_z_bottom + story_height - beam_height / 2
            beam_length_x = floor_width - column_dim
            beam_length_y = floor_depth - column_dim

            beam_x1 = trimesh.creation.box(extents=[beam_length_x, beam_width, beam_height])
            beam_x1.apply_translation([0, column_y_offset, beam_z])
            meshes.append(beam_x1)

            beam_x2 = trimesh.creation.box(extents=[beam_length_x, beam_width, beam_height])
            beam_x2.apply_translation([0, -column_y_offset, beam_z])
            meshes.append(beam_x2)

            beam_y1 = trimesh.creation.box(extents=[beam_width, beam_length_y, beam_height])
            beam_y1.apply_translation([column_x_offset, 0, beam_z])
            meshes.append(beam_y1)

            beam_y2 = trimesh.creation.box(extents=[beam_width, beam_length_y, beam_height])
            beam_y2.apply_translation([-column_x_offset, 0, beam_z])
            meshes.append(beam_y2)
        
        combined = trimesh.util.concatenate(meshes)

        # Material
        if material_type == 'wood':
            base_color = [0.6, 0.4, 0.2, 1.0]
            pbr_material = trimesh.visual.texture.PBRMaterial(
                baseColorFactor=base_color, metallicFactor=0.0, roughnessFactor=0.8)
        elif material_type == 'steel':
            base_color = [0.7, 0.7, 0.7, 1.0]
            pbr_material = trimesh.visual.texture.PBRMaterial(
                baseColorFactor=base_color, metallicFactor=0.9, roughnessFactor=0.3)
        else:  # concrete
            base_color = [0.55, 0.55, 0.55, 1.0]
            pbr_material = trimesh.visual.texture.PBRMaterial(
                baseColorFactor=base_color, metallicFactor=0.05, roughnessFactor=0.9)

        combined.visual = trimesh.visual.TextureVisuals()
        combined.visual.material = pbr_material

        if return_bytes:
            buffer = io.BytesIO()
            combined.export(buffer, file_type='glb')
            buffer.seek(0)
            return buffer.read()
        
        return combined
        
    except Exception as e:
        print(f"Error generating 3D model: {e}")
        return None


# Initialize default model (moved outside function for direct execution at startup)
try:
    initial_model_bytes = generate_with('wood', 1, 0.2, return_bytes=True)
    if initial_model_bytes:
        initial_model_id = str(uuid.uuid4())
        in_memory_models[initial_model_id] = initial_model_bytes
        print(f"Initial model created with ID: {initial_model_id}")
    else:
        print("Failed to generate initial model bytes.")
except Exception as e:
    print(f"Error generating initial 3D model: {e}")


# Endpoint to serve images
@app.get('/chart/{image_id}.png')
async def get_chart(image_id: str):
    image_bytes = in_memory_images.get(image_id)
    if image_bytes:
        return Response(content=image_bytes, media_type='image/png')
    return Response(status_code=404, content="Image not found")

# Endpoint to serve 3D models
@app.get('/model/{model_id}.glb')
async def get_model(model_id: str):
    glb_bytes = in_memory_models.get(model_id)
    if glb_bytes:
        return Response(content=glb_bytes, media_type='model/gltf-binary')
    return Response(status_code=404, content="Model not found")


# Helper functions
def pre_viga(vao_viga):
    if vao_viga < 4:
        base_viga = 150
    elif vao_viga < 6:
        base_viga = 190
    else:
        base_viga = 240
    return str(base_viga) + ' x ' + str(int(max(base_viga, vao_viga * 1000 / 10)))

# Function to update model-viewer src (now updates the content of the ui.html element)
async def update_model_viewer_src(model_id):
    global model_viewer_html_element
    model_url = f'/model/{model_id}.glb?t={time.time()}' # Add timestamp to bust cache

    if model_viewer_html_element:
        model_viewer_html_element.clear()
        with model_viewer_html_element as scene:
            scene.gltf(model_url).scale(0.5)

# Main interface
@ui.page('/')
def main_page():
    global tabs, model_viewer_html_element # Ensure access to the global ui.html element

    with ui.header().classes('bg-blue-800 text-white shadow-lg'):
        ui.label('STAMADE - Análise Estrutural').classes('text-h4 font-bold tracking-wider')
    
    ui.add_css('''
        body {
            font-family: 'Roboto', sans-serif;
            background-color: #f4f6f8;
            margin: 0;
            padding: 0;
        }
        .split-container {
            display: flex;
            height: calc(100vh - 64px); /* Adjust for header height */
            gap: 1.5rem; /* Increased gap */
            padding: 1.5rem; /* Increased padding */
            box-sizing: border-box; /* Include padding in height calculation */
        }
        .left-panel, .right-panel {
            flex: 1; /* Both panels take equal available space */
            min-width: 400px; /* Minimum width to prevent crushing */
            padding: 1.5rem;
            background-color: white;
            border-radius: 12px;
            box-shadow: 0 6px 25px rgba(0, 0, 0, 0.1); /* Stronger shadow */
            overflow-y: auto;
        }
        /* Specific adjustments for right panel to handle model-viewer */
        .right-panel > .q-column {
            height: 100%; /* Ensure column fills the panel */
        }
        .results-section {
            flex-grow: 0; /* Don't grow, take only necessary space */
        }
        .model-viewer-wrapper {
            flex-grow: 1; /* Model viewer takes remaining space */
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 300px; /* Minimum height for the viewer */
        }
        .q-tab-panel {
            padding: 1rem 0;
        }
        .q-field {
            margin-bottom: 1rem;
        }
        .q-btn {
            font-weight: 600;
            border-radius: 8px;
            padding: 0.75rem 1.5rem;
            transition: background-color 0.3s ease, transform 0.2s ease;
        }
        .q-btn:hover {
            transform: translateY(-2px);
        }
        .text-h5 {
            color: #2c3e50; /* Darker heading color */
        }
        .text-gray-700 {
            color: #34495e; /* Darker text */
        }
        .q-separator {
            background-color: #ecf0f1; /* Light separator */
            margin: 1.5rem 0;
        }
    ''')

    with ui.element('div').classes('split-container'):
        # Left panel - Calculations
        with ui.element('div').classes('left-panel'):
            with ui.tabs().classes('w-full') as tabs_container:
                laje_tab = ui.tab('Laje', icon='layers')
                viga_tab = ui.tab('Viga', icon='horizontal_rule')
                pilar_tab = ui.tab('Pilar', icon='vertical_align_center')
            tabs = tabs_container # Assign to global tabs variable
            
            with ui.tab_panels(tabs_container, value=laje_tab).classes('w-full'):
                with ui.tab_panel(laje_tab):
                    criar_painel_laje()
                
                with ui.tab_panel(viga_tab):
                    criar_painel_viga()
                
                with ui.tab_panel(pilar_tab):
                    criar_painel_pilar()
        
        # Right panel - Results
        with ui.element('div').classes('right-panel'):
            with ui.column().classes('w-full h-full'): # Ensure column fills the height
                criar_painel_resultados() # This creates results_text and chart_html
                
                ui.separator().classes('my-4') # Separator between charts/text and model viewer

                # This is the key change: create the ui.html element directly in the right panel
                # It acts as a container for the model-viewer
                # The model_viewer_html_element global variable holds a reference to this ui.html component
                model_viewer_html_element = ui.scene().classes('w-full model-viewer-wrapper')
                
                # Initially render the model viewer with the default model
                if initial_model_id:
                    initial_model_url = f'/model/{initial_model_id}.glb?t={time.time()}'
                    with model_viewer_html_element as scene:
                        scene.gltf(initial_model_url).scale(0.5)
                else:
                    model_viewer_html_element.content = '<div class="text-gray-500 text-center">Modelo 3D não disponível. Tente gerar novamente.</div>'


# Function to create slab panel
def criar_painel_laje():
    with ui.column().classes('w-full gap-4'):
        ui.label('Configuração da Laje').classes('text-h5 font-semibold text-gray-800 mb-4')
        
        tipo_laje = ui.select(['Madeira', 'Concreto', 'Aço'], label='Tipo de Laje', value='Madeira').classes('w-full')
            
        ui.separator()
        ui.label('Dimensões do Grid (m)').classes('text-lg font-medium text-gray-700')
        with ui.row().classes('w-full justify-around'):
            grid_x = ui.number(label='Grid X', value=5.0, format='%.2f', step=0.1).classes('w-1/2 pr-2')
            grid_y = ui.number(label='Grid Y', value=5.0, format='%.2f', step=0.1).classes('w-1/2 pl-2')
        
        ui.separator()
        ui.label('Cargas (kN/m²)').classes('text-lg font-medium text-gray-700')
        with ui.row().classes('w-full justify-around'):
            gk = ui.number(label='Carga Permanente (Gk)', value=1.0, format='%.2f', step=0.1).classes('w-1/2 pr-2')
            qk = ui.number(label='Carga Variável (Qk)', value=2.0, format='%.2f', step=0.1).classes('w-1/2 pl-2')
        
        ui.separator()
        ui.label('Outros Parâmetros').classes('text-lg font-medium text-gray-700')
        with ui.row().classes('w-full justify-around'):
            trrf = ui.number(label='TRRF (min)', value=30, format='%d').classes('w-1/2 pr-2')
            area = ui.number(label='Área do Pavimento (m²)', value=100, format='%.2f', step=10).classes('w-1/2 pl-2')
        
        with ui.row().classes('w-full justify-around'):
            pavimentos = ui.number(label='Número de Pavimentos', value=1, format='%d').classes('w-1/2 pr-2')
            coberturas = ui.number(label='Número de Coberturas', value=1, format='%d').classes('w-1/2 pl-2')
            
        ui.button('Calcular Laje', on_click=lambda: executar_laje(
            tipo_laje.value, grid_x.value, grid_y.value, gk.value, qk.value,
            trrf.value, area.value, pavimentos.value, coberturas.value
        )).classes('w-full bg-green-600 text-white hover:bg-green-700 mt-4')

# Function to create beam panel
def criar_painel_viga():
    with ui.column().classes('w-full gap-4'):
        ui.label('Configuração da Viga').classes('text-h5 font-semibold text-gray-800 mb-4')
        
        tipo_viga = ui.select(['Madeira', 'Concreto', 'Aço'], label='Tipo de Viga', value='Madeira').classes('w-full')
            
        ui.separator()
        ui.label('Massas Específicas (kg/m³)').classes('text-lg font-medium text-gray-700')
        with ui.row().classes('w-full justify-around'):
            gama_viga = ui.number(label='Gama Vigas Piso', value=550, format='%.0f').classes('w-1/2 pr-2')
            gama_viga_cob = ui.number(label='Gama Vigas Cobertura', value=550, format='%.0f').classes('w-1/2 pl-2')
            
        ui.separator()
        ui.label('Dimensões da Viga de Cobertura (mm)').classes('text-lg font-medium text-gray-700')
        with ui.row().classes('w-full justify-around'):
            base_viga_cob = ui.number(label='Base', value=150, format='%.0f').classes('w-1/2 pr-2')
            altura_viga_cob = ui.number(label='Altura', value=300, format='%.0f').classes('w-1/2 pl-2')
            
        viga_cobertura_igual = ui.checkbox('Viga de Cobertura Igual a de Piso?', value=True).classes('w-full mt-2')
            
        ui.button('Calcular Viga', on_click=lambda: executar_viga(
            tipo_viga.value, gama_viga.value, gama_viga_cob.value, 
            base_viga_cob.value, altura_viga_cob.value, viga_cobertura_igual.value
        )).classes('w-full bg-green-600 text-white hover:bg-green-700 mt-4')

# Function to create pillar panel
def criar_painel_pilar():
    with ui.column().classes('w-full gap-4'):
        ui.label('Configuração do Pilar').classes('text-h5 font-semibold text-gray-800 mb-4')
        
        tipo_pilar = ui.select(['Madeira', 'Concreto', 'Aço'], label='Tipo de Pilar', value='Madeira').classes('w-full')
            
        ui.separator()
        gama_pilar = ui.number(label='Gama Pilar (kg/m³)', value=550, format='%.0f').classes('w-full')
            
        ui.button('Calcular Pilar', on_click=lambda: executar_pilar(
            tipo_pilar.value, gama_pilar.value
        )).classes('w-full bg-green-600 text-white hover:bg-green-700 mt-4')

# Function to create results panel
def criar_painel_resultados():
    global resultado_text, resultado_grafico_html
    
    with ui.column().classes('w-full results-section'): # Added results-section class for layout control
        ui.label('Resultados da Análise Estrutural').classes('text-h5 font-semibold text-gray-800 mb-4')
        
        resultado_text = ui.label('Os resultados detalhados aparecerão aqui após os cálculos.').classes('text-gray-700 text-base leading-relaxed mb-4') # Added leading-relaxed
        
        ui.separator().classes('my-4')

        with ui.row().classes('w-full justify-evenly items-center mb-4'):
            ui.button('Gerar Gráficos de Análise', on_click=gerar_graficos, icon='bar_chart').classes('bg-blue-600 text-white hover:bg-blue-700')
            ui.button('Visualizar Modelo 3D', on_click=gerar_modelo_3d, icon='3d_rotation').classes('bg-purple-600 text-white hover:bg-purple-700')
        
        resultado_grafico_html = ui.html('').classes('w-full flex justify-center mt-4')
        # The model_viewer_html_element is created in main_page, not here,
        # so it lives outside this specific card for better layout control.


# Function to generate graphics
async def gerar_graficos():
    try:
        if not lista_resultados:
            ui.notify('Por favor, execute os cálculos da laje, viga e pilar primeiro para gerar os gráficos.', color='negative', icon='warning')
            return

        fig, axs = plt.subplots(2, 2, figsize=(12, 10), dpi=100)
        
        cores = ['#4CAF50', '#2196F3', '#FFC107'] # More pleasant colors
        materiais = ['Madeira', 'Concreto', 'Aço']
        
        # Simulate costs, carbon, and weight based on calculated material types
        custos = [10000, 15000, 20000]
        carbono = [500, 1000, 1500]
        peso = [1000, 2000, 3000]

        # Try to get the calculated slab type for solution 0 to influence graph data
        if lista_resultados: # Ensure lista_resultados is not empty
            current_material_type = lista_resultados[0].get('Tipo Laje', 'Madeira')
            if current_material_type == 'Madeira':
                custos = [9000, 16000, 21000]
                carbono = [400, 1100, 1600]
                peso = [900, 2100, 3100]
            elif current_material_type == 'Concreto':
                custos = [18000, 12000, 19000]
                carbono = [1200, 600, 1400]
                peso = [2500, 1500, 2800]
            elif current_material_type == 'Aço':
                custos = [15000, 18000, 10000]
                carbono = [1100, 1300, 500]
                peso = [1800, 2200, 1200]

        # Cost Chart
        axs[0, 0].pie(custos, labels=materiais, autopct='%1.1f%%', startangle=90, colors=cores, wedgeprops={'edgecolor': 'black'})
        axs[0, 0].set_title('Custo Estimado por Material', fontsize=14, fontweight='bold')
        
        # Carbon Chart
        axs[0, 1].pie(carbono, labels=materiais, autopct='%1.1f%%', startangle=90, colors=cores, wedgeprops={'edgecolor': 'black'})
        axs[0, 1].set_title('Pegada de Carbono por Material', fontsize=14, fontweight='bold')
        
        # Weight Chart
        axs[1, 0].pie(peso, labels=materiais, autopct='%1.1f%%', startangle=90, colors=cores, wedgeprops={'edgecolor': 'black'})
        axs[1, 0].set_title('Peso Total por Material', fontsize=14, fontweight='bold')
        
        # Simplified Structural Drawing
        axs[1, 1].set_xlim(0, 10)
        axs[1, 1].set_ylim(0, 6.2)
        axs[1, 1].axis('off') # Hide axes for a cleaner look
        
        # Pillar
        pilar_rect = patches.Rectangle((4.5, 0), 1, 5.0, facecolor='#607D8B', edgecolor='black', linewidth=1.5) # Dark gray
        axs[1, 1].add_patch(pilar_rect)
        axs[1, 1].text(5.0, 2.5, 'Pilar', ha='center', va='center', fontsize=12, color='white', fontweight='bold')
        
        # Beams
        # Top left beam
        axs[1, 1].add_patch(patches.Rectangle((2, 5), 2.5, 0.4, facecolor='#795548', edgecolor='black', linewidth=1.5)) # Brown
        # Top right beam
        axs[1, 1].add_patch(patches.Rectangle((6.5, 5), 2.5, 0.4, facecolor='#795548', edgecolor='black', linewidth=1.5)) # Brown
        # Transversal beam (passing over the pillar)
        axs[1, 1].add_patch(patches.Rectangle((2, 5.4), 6, 0.4, facecolor='#795548', edgecolor='black', linewidth=1.5)) # Brown
        axs[1, 1].text(5, 5.2, 'Vigas', ha='center', va='center', fontsize=12, color='white', fontweight='bold')

        # Slab
        laje_rect = patches.Rectangle((1.5, 5.8), 7, 0.4, facecolor='#9E9E9E', edgecolor='black', linewidth=1.5) # Light gray
        axs[1, 1].add_patch(laje_rect)
        axs[1, 1].text(5.0, 6.0, 'Laje', ha='center', va='center', fontsize=12, color='black', fontweight='bold')
        
        axs[1, 1].set_title('Representação Estrutural Simplificada', fontsize=14, fontweight='bold')
        
        plt.tight_layout(pad=3.0) # Add padding to avoid cropping
        
        buf = io.BytesIO()
        fig.savefig(buf, format='png', bbox_inches='tight', facecolor='white', dpi=100)
        buf.seek(0)
        
        image_id = str(uuid.uuid4())
        in_memory_images[image_id] = buf.getvalue()
        
        image_url = f'/chart/{image_id}.png?t={time.time()}'
        resultado_grafico_html.content = f'<img src="{image_url}" class="max-w-full h-auto" alt="Gráficos de Análise">'
        
        plt.close(fig)
        
        ui.notify('Gráficos gerados com sucesso!', color='positive', icon='check_circle')
        
    except Exception as e:
        ui.notify(f'Erro ao gerar gráficos: {str(e)}', color='negative', icon='error')

# Function to generate 3D model
async def gerar_modelo_3d():
    try:
        if not lista_resultados:
            ui.notify('Por favor, execute os cálculos da laje, viga e pilar primeiro para gerar o modelo 3D.', color='negative', icon='warning')
            return
            
        solucao = 0
        material_map = {'Madeira': 'wood', 'Concreto': 'concrete', 'Aço': 'steel'}
        material_type = material_map.get(lista_resultados[solucao].get('Tipo Laje', 'Madeira'), 'wood')
        num_floors = lista_resultados[solucao].get('Pavimentos', 1)
        thickness = lista_resultados[solucao].get('Secao Laje', 200) / 1000 if 'Secao Laje' in lista_resultados[solucao] else 0.2
        
        glb_bytes = generate_with(material_type, num_floors, thickness, return_bytes=True)

        if glb_bytes:
            model_id = str(uuid.uuid4())
            in_memory_models[model_id] = glb_bytes

            await update_model_viewer_src(model_id)  # Update the model-viewer with the new model
            
            ui.notify('Modelo 3D gerado com sucesso!', color='positive', icon='3d_rotation')
        else:
            ui.notify('Erro ao gerar modelo 3D: O modelo retornado é nulo.', color='negative', icon='error')
            
    except Exception as e:
        ui.notify(f'Erro ao gerar modelo 3D: {str(e)}', color='negative', icon='error')

# Execution functions
def executar_laje(tipo_laje, grid_x, grid_y, gk, qk, trrf, area, pavimentos, coberturas):
    solucao = 0
    if len(lista_resultados) <= solucao:
        lista_resultados.append({})
    
    vao_laje = min(grid_x, grid_y)
    secao_laje = max(80, round(0.0286 * (vao_laje * 100), 0) * 10)
    
    lista_resultados[solucao]['Tipo Laje'] = tipo_laje
    lista_resultados[solucao]['Secao Laje'] = secao_laje
    lista_resultados[solucao]['Area'] = area
    lista_resultados[solucao]['Pavimentos'] = pavimentos
    lista_resultados[solucao]['Coberturas'] = coberturas
    lista_resultados[solucao]['Grid X'] = grid_x
    lista_resultados[solucao]['Grid Y'] = grid_y
    
    ui.notify(f'Laje calculada com sucesso! Seção: **{secao_laje} mm**', color='positive', icon='check')
    tabs.set_value('Viga') # Uses the tab name to change

def executar_viga(tipo_viga, gama_viga, gama_viga_cob, base_viga_cob, altura_viga_cob, viga_cobertura_igual):
    solucao = 0
    if len(lista_resultados) <= solucao or 'Secao Laje' not in lista_resultados[solucao]:
        ui.notify('Por favor, calcule a laje primeiro.', color='negative', icon='warning')
        return
    
    vao_viga = max(lista_resultados[solucao]['Grid X'], lista_resultados[solucao]['Grid Y'])
    secao_viga = pre_viga(vao_viga)
    
    lista_resultados[solucao]['Tipo Viga'] = tipo_viga
    lista_resultados[solucao]['Secao Viga'] = secao_viga
    lista_resultados[solucao]['Gama Viga'] = gama_viga
    lista_resultados[solucao]['Gama Viga Cobertura'] = gama_viga_cob
    lista_resultados[solucao]['Base Viga Cobertura'] = base_viga_cob
    lista_resultados[solucao]['Altura Viga Cobertura'] = altura_viga_cob
    
    ui.notify(f'Viga calculada com sucesso! Seção: **{secao_viga}**', color='positive', icon='check')
    tabs.set_value('Pilar') # Uses the tab name to change

def executar_pilar(tipo_pilar, gama_pilar):
    solucao = 0
    if len(lista_resultados) <= solucao or 'Secao Viga' not in lista_resultados[solucao]:
        ui.notify('Por favor, calcule a laje e a viga primeiro.', color='negative', icon='warning')
        return
    
    # Simplified example, you can add pillar calculation logic here
    secao_pilar = '200 x 300'
    
    lista_resultados[solucao]['Tipo Pilar'] = tipo_pilar
    lista_resultados[solucao]['Secao Pilar'] = secao_pilar
    lista_resultados[solucao]['Gama Pilar'] = gama_pilar
    
    # Update result text
    resultado_text.set_text(
        f'Resultados Finais:\n'
        f'- Laje: **{lista_resultados[solucao]["Secao Laje"]} mm** ({lista_resultados[solucao]["Tipo Laje"]})\n'
        f'- Viga: **{lista_resultados[solucao]["Secao Viga"]}** ({lista_resultados[solucao]["Tipo Viga"]})\n'
        f'- Pilar: **{secao_pilar}** ({lista_resultados[solucao]["Tipo Pilar"]})'
    )
    ui.notify(f'Pilar calculado com sucesso! Seção: **{secao_pilar}**. Análise Completa!', color='positive', icon='done_all')
    tabs.set_value('Laje') # Returns to the first tab or you can create a "Summary" tab

ui.run(title='STAMADE - Análise Estrutural', dark=False)