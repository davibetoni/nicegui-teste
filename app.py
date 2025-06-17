from nicegui import ui, app
from fastapi.responses import Response
import os
from building_model import generate_with
import urllib.parse
import uuid # For generating unique IDs for each model
import time
import sys

# Setup pasta static (still useful for other static files like images, etc., but not for the generated GLBs)
os.makedirs("static", exist_ok=True)
app.add_static_files('/static', os.path.join(os.getcwd(), 'static'))

# Dictionary to store the generated GLB bytes in memory
# Key: model_id (UUID string), Value: glb_bytes (bytes object)
in_memory_models = {}

# These global variables will hold references to the NiceGUI UI components (ui.select, ui.number)
# They are initialized to None here, and will be assigned when the page is built in home().
current_material_type: ui.select = None
current_num_floors: ui.number = None

# --- NEW: FastAPI Endpoint to serve GLB dynamically from memory ---
@app.get('/model/{model_id}.glb')
async def get_model(model_id: str):
    glb_bytes = in_memory_models.get(model_id)
    if glb_bytes:
        return Response(content=glb_bytes, media_type='model/gltf-binary')
    print(f"ERROR: Model with ID {model_id} not found in in_memory_models. This might indicate a missing model or cleanup issue.") # Debug
    return Response(status_code=404, content="Model not found")

# --- INITIALIZATION OF THE FIRST MODEL IN MEMORY WHEN THE APPLICATION STARTS ---
# This ensures that when the first user accesses the page, there's already a model to display.
initial_material_default = 'wood'
initial_floors_default = 1
initial_model_bytes = generate_with(initial_material_default, initial_floors_default, return_bytes=True)

# Generate a unique ID for the initial model
initial_model_id = str(uuid.uuid4())
if initial_model_bytes:
    in_memory_models[initial_model_id] = initial_model_bytes
    sys.stderr.write(f"DEBUG: Initial model generated in memory with ID: {initial_model_id}\n")
else:
    sys.stderr.write("DEBUG: Failed to generate initial model in memory. The app might not display a model on first load.\n")
    # If initial generation fails, set initial_model_id to None so the UI knows not to try loading it.
    initial_model_id = None 

# The 'home' function defines the content and layout of your web page.
@ui.page('/')
async def home():
    # Declare globals used within this function to modify them.
    # These refer to the ui.select and ui.number components.
    global current_material_type, current_num_floors 

    # --- HTML container for the model-viewer ---
    # This ui.html component is created here so NiceGUI manages its position in the layout.
    # It will contain the <model-viewer> tag.
    model_viewer_html_content = ""
    if initial_model_id: # Check if the initial model was successfully generated
        # The src attribute points to our dynamic FastAPI endpoint
        model_viewer_html_content = f'''
            <script type="module" src="https://unpkg.com/@google/model-viewer/dist/model-viewer.min.js"></script>  
            <model-viewer
                id="my-dynamic-model-viewer"
                src="/model/{initial_model_id}.glb?_t={time.time()}"
                auto-rotate
                camera-controls
                shadow-intensity="1"
                exposure="1"
                style="width: 100%; height: 600px; background: #f0f0f0; border: 2px solid blue;"
                alt="3D Building Structure Model">
            </model-viewer>
        '''
    else:
        # Fallback content if the initial model could not be generated
        model_viewer_html_content = '<div style="width: 100%; height: 600px; display: flex; align-items: center; justify-content: center; background: #f0f0f0; border: 2px solid red;">Error: Failed to load initial model. Please check server logs.</div>'
    
    # Create the ui.html component; it will be displayed later by simply putting its variable name.
    model_viewer_component = ui.add_body_html(model_viewer_html_content)
    
    # --- Asynchronous function to update the model-viewer's src attribute via JavaScript ---
    # This is called after a new model is generated to update the display without a full page reload.
    async def update_model_viewer_src(model_id_to_display: str):
        # Construct the URL for the new model, adding a timestamp to bypass browser cache
        model_url = f'/model/{model_id_to_display}.glb?_t={time.time()}'
        sys.stderr.write(f"DEBUG: Attempting to update model-viewer SRC to: {model_url}\n")
        
        # Execute JavaScript in the user's browser to update the model-viewer's 'src'
        await ui.run_javascript(f'''
            const modelViewer = document.getElementById("my-dynamic-model-viewer");
            if (modelViewer) {{
                modelViewer.src = '{model_url}';
                // Optional: Force reload if the model isn't updating visibly
                // modelViewer.load(); 
                console.log('JS: model-viewer SRC updated to: ' + modelViewer.src);
            }} else {{
                console.error("JS: Model-viewer element not found with ID 'my-dynamic-model-viewer'.");
            }}
        ''', timeout=5.0)


    # --- UI Layout Starts Here ---
    ui.label('Gerador de Estruturas de Prédio 3D').classes('text-h5 q-mb-md')

    with ui.card().classes('w-full items-center'):
        ui.label('Configuração da Estrutura').classes('text-h6')
        with ui.row().classes('items-center q-gutter-md'):
            ui.label('Material:').classes('text-subtitle1')
            # Assign the created ui.select component to the global variable.
            # The 'value' is set to the default material for consistency.
            current_material_type = ui.select(['wood', 'steel', 'concrete'], value=initial_material_default).classes('w-32') 

            ui.label('Andares:').classes('text-subtitle1')
            # Assign the created ui.number component to the global variable.
            # The 'value' is set to the default number of floors.
            current_num_floors = ui.number(label='Número de Andares', value=initial_floors_default, min=1, max=10, step=1).classes('w-28')
            
            # --- Event handler for the "Gerar Prédio" button ---
            async def on_generate_click_multiusuario():
                # Generate the GLB as bytes using the building_model.py function
                glb_bytes = generate_with(current_material_type.value, current_num_floors.value, return_bytes=True)
                
                if glb_bytes is None:
                    ui.notify('Falha ao gerar o modelo. Verifique o terminal para detalhes.', type='negative')
                    return

                # Generate a new unique ID for this newly generated model
                model_id = str(uuid.uuid4())
                in_memory_models[model_id] = glb_bytes # Store the bytes in our in-memory dictionary

                sys.stderr.write(f'DEBUG: Model GLB generated in memory with ID: {model_id}\n')
                
                # Update the model-viewer in the user's browser using JavaScript
                await update_model_viewer_src(model_id)
                ui.notify('Modelo atualizado!', type='positive')

            ui.button('Gerar Prédio', on_click=on_generate_click_multiusuario, icon='architecture').classes('q-ml-md')

    # Add a visual separator between the controls and the model viewer
    ui.separator().classes('q-my-md') 

    # --- Display the model-viewer component ---
    # Since model_viewer_component was already created above, simply referencing it adds it to the layout flow.
    model_viewer_component 

# Run the NiceGUI application
ui.run(title='NiceGUI Building Generator (Multiuser)', port=8080)