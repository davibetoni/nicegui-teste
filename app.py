from nicegui import ui

@ui.page('/')
def main_page():
    ui.label('Bem-vindo ao FinGuide')
    ui.button('Clique aqui', on_click=lambda: ui.notify('Você clicou!'))

ui.run(title='FinGuide App', reload=False)
