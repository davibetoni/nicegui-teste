# ... (imports e setup inicial)
from nicegui import ui, app
import os
from building_model import generate_with
import urllib.parse
import time
import sys

# Setup pasta static
os.makedirs("static", exist_ok=True)
app.add_static_files('/static', os.path.join(os.getcwd(), 'static'))

generated_glb_files = [] 
current_displayed_filename = None 

ui.add_head_html('<script type="module" src="https://unpkg.com/@google/model-viewer/dist/model-viewer.min.js"></script>')

# Estas variáveis globais serão usadas pelos controles na interface
current_material_type = None
current_num_floors = None
filename = None # Continua a ser o nome do último arquivo GLB gerado (global)


def on_generate_click():
    global generated_glb_files, current_material_type, current_num_floors, filename

    # Gerar o novo modelo com base nas seleções atuais
    new_filename_full_path = generate_with(current_material_type.value, current_num_floors.value)
    
    if new_filename_full_path is None:
        ui.notify('Falha ao gerar o modelo. Verifique o terminal para detalhes.', type='negative')
        return

    sys.stderr.write(f'DEBUG: Arquivo GLB gerado: {new_filename_full_path}\n')
    
    generated_glb_files.append(os.path.basename(new_filename_full_path))

    # Limpa arquivos antigos
    files_to_keep = 2 
    if len(generated_glb_files) > files_to_keep:
        for old_file in generated_glb_files[:-files_to_keep]:
            old_filepath = os.path.join('static', old_file)
            if os.path.exists(old_filepath):
                try:
                    os.remove(old_filepath)
                    sys.stderr.write(f"DEBUG: Removido arquivo antigo: {old_file}\n")
                except Exception as e:
                    sys.stderr.write(f"DEBUG: Erro ao remover {old_file}: {e}\n")
        generated_glb_files = generated_glb_files[-files_to_keep:]

    # AQUI: Atribui o novo caminho ao 'filename' global antes de recarregar
    filename = new_filename_full_path 
    ui.navigate.reload()


@ui.page('/')
async def home():
    ui.label('Gerador de Estruturas de Prédio 3D').classes('text-h5 q-mb-md')

    with ui.card().classes('w-full items-center'):
        ui.label('Configuração da Estrutura').classes('text-h6')
        with ui.row().classes('items-center q-gutter-md'):
            ui.label('Material:').classes('text-subtitle1')
            global current_material_type
            # ADICIONADO 'concrete' AQUI
            current_material_type = ui.select(['wood', 'steel', 'concrete'], value='wood').classes('w-32') 

            ui.label('Andares:').classes('text-subtitle1')
            global current_num_floors
            current_num_floors = ui.number(label='Número de Andares', value=1, min=1, max=10, step=1).classes('w-28')
            
            ui.button('Gerar Prédio', on_click=on_generate_click, icon='architecture').classes('q-ml-md')

    ui.separator().classes('q-my-md')

    global filename # Declara para poder usar/modificar o global 'filename'

    # Gerar o modelo inicial quando a página é carregada pela primeira vez
    if not filename:
        sys.stderr.write("DEBUG: Gerando modelo inicial na primeira carga da página.\n")
        initial_material = current_material_type.value if current_material_type else 'wood'
        initial_floors = int(current_num_floors.value) if current_num_floors else 1
        
        filename = generate_with(initial_material, initial_floors)
        if filename:
            generated_glb_files.append(os.path.basename(filename))
            sys.stderr.write(f"DEBUG: Modelo inicial gerado: {filename}\n")
        else:
            sys.stderr.write("DEBUG: Falha ao gerar modelo inicial.\n")
            ui.notify("Falha ao gerar modelo inicial da estrutura.", type='warning')

    if filename:
        model_viewer_element_id = "my-model-viewer" # ID fixo para o model-viewer
        ui.add_body_html(f'''
        <model-viewer 
            id="{model_viewer_element_id}"
            src="/static/{os.path.basename(filename)}?_t={time.time()}"
            auto-rotate 
            camera-controls 
            shadow-intensity="1"
            exposure="1"
            style="width: 100%; height: 600px; background: #f0f0f0; border: 2px solid blue;"
            alt="Modelo 3D da Estrutura de Prédio">
        </model-viewer>
        ''')
        sys.stderr.write(f"DEBUG: model-viewer HTML injetado com SRC: /static/{os.path.basename(filename)}\n")
    else:
        ui.label('Nenhum modelo gerado ou carregado.').classes('q-mt-md')


ui.run(title='NiceGUI Builder', port=8080)