"""
Versão Simplificada do Detector de Buracos
Esta versão usa apenas Kivy sem OpenCV para testar o build primeiro
"""

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.camera import Camera
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle
from datetime import datetime

# Importar permissões do Android
try:
    from android.permissions import request_permissions, Permission
    ANDROID = True
except ImportError:
    ANDROID = False


class SimplePotholeApp(BoxLayout):
    """Interface simplificada para teste"""
    
    def __init__(self, **kwargs):
        super(SimplePotholeApp, self).__init__(**kwargs)
        self.orientation = 'vertical'
        
        # Status label
        self.status_label = Label(
            text='Detector de Buracos v1.0',
            size_hint=(1, 0.15),
            font_size='24sp',
            color=(0, 1, 0, 1)
        )
        
        # Placeholder para câmera (será iniciada após permissões)
        self.camera = Label(
            text='Solicitando permissão da câmera...',
            size_hint=(1, 0.65),
            font_size='18sp'
        )
        
        # Info label
        self.info_label = Label(
            text='Aguardando permissões...',
            size_hint=(1, 0.1),
            font_size='16sp'
        )
        
        # Botão de teste
        self.test_button = Button(
            text='Simular Detecção',
            size_hint=(1, 0.1),
            on_press=self.simulate_detection
        )
        
        # Adiciona widgets
        self.add_widget(self.status_label)
        self.add_widget(self.camera)
        self.add_widget(self.info_label)
        self.add_widget(self.test_button)
        
        # Contador
        self.detection_count = 0
        
        # Solicitar permissões no Android
        if ANDROID:
            request_permissions([Permission.CAMERA, Permission.WRITE_EXTERNAL_STORAGE], self.on_permissions_result)
        else:
            # Desktop - iniciar câmera diretamente
            self.init_camera()
        
        # Atualiza timestamp
        Clock.schedule_interval(self.update_time, 1.0)
    
    def on_permissions_result(self, permissions, grant_results):
        """Callback quando permissões são concedidas/negadas"""
        if all(grant_results):
            self.init_camera()
            self.info_label.text = 'Permissões concedidas - Câmera ativa'
        else:
            self.camera.text = '❌ Permissão de câmera negada!\nPor favor, habilite nas configurações do app.'
            self.info_label.text = 'Sem permissões - Funcionalidade limitada'
    
    def init_camera(self):
        """Inicializa a câmera após permissões concedidas"""
        try:
            # Remove o label placeholder
            self.remove_widget(self.camera)
            
            # Cria câmera
            self.camera = Camera(
                resolution=(640, 480),
                play=True,
                index=0  # 0 = câmera traseira
            )
            
            # Adiciona na posição correta (após status_label)
            self.add_widget(self.camera, index=len(self.children) - 1)
            self.info_label.text = 'Câmera ativa - Aguardando detecção...'
            
        except Exception as e:
            self.camera = Label(text=f'Erro ao acessar câmera: {e}')
            self.add_widget(self.camera, index=len(self.children) - 1)
    
    def update_time(self, dt):
        """Atualiza timestamp"""
        current_time = datetime.now().strftime('%H:%M:%S')
        self.info_label.text = f'Sistema ativo - {current_time}'
    
    def simulate_detection(self, instance):
        """Simula uma detecção de buraco"""
        self.detection_count += 1
        self.status_label.text = f'⚠️ BURACO DETECTADO! Total: {self.detection_count}'
        self.status_label.color = (1, 0, 0, 1)
        
        # Volta ao normal após 2 segundos
        Clock.schedule_once(self.reset_status, 2.0)
    
    def reset_status(self, dt):
        """Reseta status"""
        self.status_label.text = 'Detector de Buracos v1.0'
        self.status_label.color = (0, 1, 0, 1)


class PotholeDetectorApp(App):
    """App principal"""
    
    def build(self):
        self.title = 'Detector de Buracos'
        return SimplePotholeApp()
    
    def on_pause(self):
        return True
    
    def on_resume(self):
        pass


if __name__ == '__main__':
    PotholeDetectorApp().run()
