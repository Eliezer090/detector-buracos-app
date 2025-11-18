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
        
        # Câmera
        try:
            self.camera = Camera(
                resolution=(640, 480),
                play=True,
                index=0
            )
        except Exception as e:
            self.camera = Label(text=f'Erro ao acessar câmera: {e}')
        
        # Info label
        self.info_label = Label(
            text='Câmera ativa - Aguardando detecção...',
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
        
        # Atualiza timestamp
        Clock.schedule_interval(self.update_time, 1.0)
    
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
