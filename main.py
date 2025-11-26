"""
Detector de Buracos - Aplicativo Android
=========================================
Usa câmera traseira + IA para detectar buracos na pista em tempo real.
"""

import os
from datetime import datetime
from typing import List, Tuple

# Kivy config DEVE vir antes de qualquer outro import do Kivy
os.environ.setdefault('KIVY_LOG_LEVEL', 'info')

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Line, Rectangle
from kivy.logger import Logger
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.utils import platform

# Detecção de plataforma
IS_ANDROID = platform == "android"

# Imports condicionais para Android
if IS_ANDROID:
    try:
        from android.permissions import Permission, check_permission, request_permissions
        from jnius import autoclass
        
        PythonActivity = autoclass('org.kivy.android.PythonActivity')
        Context = autoclass('android.content.Context')
    except ImportError as e:
        Logger.warning(f"Android imports failed: {e}")
        Permission = check_permission = request_permissions = None
        PythonActivity = Context = None
else:
    Permission = check_permission = request_permissions = None
    PythonActivity = Context = None


class AlertOverlay(Widget):
    """Overlay visual para mostrar detecções na tela."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._detections: List[Tuple[float, float, float, float, float]] = []
        self.bind(pos=self._update_canvas, size=self._update_canvas)

    def _update_canvas(self, *_):
        """Redesenha quando posição/tamanho mudam."""
        self.show_detections(self._detections)

    def show_detections(self, detections: List[Tuple[float, float, float, float, float]], camera_widget=None):
        """Desenha caixas vermelhas ao redor das detecções - apenas na área da câmera."""
        self._detections = detections or []
        self.canvas.after.clear()

        if not detections:
            return

        # Usa dimensões da câmera se disponível, senão usa o widget
        cam = camera_widget
        if cam and cam.texture:
            # Calcula área real da câmera (respeitando keep_ratio)
            tex_w, tex_h = cam.texture.size
            widget_w, widget_h = cam.size
            widget_x, widget_y = cam.pos
            
            # Calcula escala mantendo proporção
            scale = min(widget_w / tex_w, widget_h / tex_h)
            cam_w = tex_w * scale
            cam_h = tex_h * scale
            cam_x = widget_x + (widget_w - cam_w) / 2
            cam_y = widget_y + (widget_h - cam_h) / 2
        else:
            cam_x, cam_y = self.x, self.y
            cam_w, cam_h = self.width, self.height

        with self.canvas.after:
            # Desenha apenas as caixas de detecção (sem overlay vermelho geral)
            for x_norm, y_norm, w_norm, h_norm, conf in detections:
                # Cor baseada na confiança
                Color(1, 0, 0, min(conf + 0.3, 1.0))
                
                x = cam_x + x_norm * cam_w
                y = cam_y + (1 - y_norm - h_norm) * cam_h
                w = w_norm * cam_w
                h = h_norm * cam_h
                
                # Caixa de detecção
                Line(rectangle=(x, y, w, h), width=3)
                
                # Label de confiança
                Color(1, 1, 0, 1)
                Line(rectangle=(x, y + h, w * conf, 5), width=5)

    def clear(self):
        """Limpa todas as detecções."""
        self._detections = []
        self.canvas.after.clear()


class PotholeDetectorLayout(BoxLayout):
    """Layout principal do aplicativo."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.padding = 10
        self.spacing = 5

        # Estado
        self.camera = None
        self.detector = None
        self.processing_event = None
        self.detection_count = 0
        self.last_alert_time = None
        self.alert_cooldown = 2.0

        # UI Components
        self.status_label = Label(
            text="[b]Detector de Buracos[/b]\nIniciando...",
            markup=True,
            size_hint=(1, 0.12),
            font_size="18sp",
            halign="center",
            valign="middle"
        )
        self.status_label.bind(size=lambda *_: setattr(
            self.status_label, 'text_size', self.status_label.size))

        self.counter_label = Label(
            text="Buracos detectados: 0",
            size_hint=(1, 0.08),
            font_size="16sp",
            color=(1, 1, 0, 1)
        )

        # Container para câmera
        self.camera_container = FloatLayout(size_hint=(1, 0.7))
        self.camera_placeholder = Label(
            text="Aguardando permissão da câmera...",
            halign="center"
        )
        self.camera_container.add_widget(self.camera_placeholder)

        # Overlay para detecções
        self.alert_overlay = AlertOverlay()
        self.camera_container.add_widget(self.alert_overlay)

        # Botão de permissão
        self.permission_btn = Button(
            text="Permitir Câmera",
            size_hint=(1, 0.1),
            opacity=0,
            disabled=True
        )
        self.permission_btn.bind(on_press=lambda *_: self._request_permissions())

        # Montar layout
        self.add_widget(self.status_label)
        self.add_widget(self.counter_label)
        self.add_widget(self.camera_container)
        self.add_widget(self.permission_btn)

        # Inicialização
        Clock.schedule_once(self._initialize, 0.5)

    def _initialize(self, *_):
        """Inicializa detector e solicita permissões."""
        try:
            from detector import PotholeDetector
            self.detector = PotholeDetector()
            Logger.info("App: Detector inicializado com sucesso")
        except Exception as e:
            Logger.error(f"App: Erro ao inicializar detector: {e}")
            self._update_status(f"Erro: {e}", error=True)
            return

        if IS_ANDROID:
            self._request_permissions()
        else:
            self._init_camera()

    def _request_permissions(self):
        """Solicita permissões no Android."""
        if not IS_ANDROID or not request_permissions:
            self._init_camera()
            return

        if check_permission and check_permission(Permission.CAMERA):
            Logger.info("App: Permissão de câmera já concedida")
            self._init_camera()
            return

        self._update_status("Solicitando permissão...")
        
        def callback(permissions, grants):
            Logger.info(f"App: Callback permissões: {permissions} -> {grants}")
            if grants and all(grants):
                Clock.schedule_once(lambda *_: self._init_camera(), 0.2)
            else:
                self._on_permission_denied()

        request_permissions([Permission.CAMERA], callback)

    def _on_permission_denied(self):
        """Tratamento quando permissão é negada."""
        self.camera_placeholder.text = (
            "❌ Permissão Negada\n\n"
            "Para usar o detector:\n"
            "1. Vá em Configurações\n"
            "2. Apps > Detector de Buracos\n"
            "3. Permissões > Câmera > Permitir"
        )
        self.permission_btn.opacity = 1
        self.permission_btn.disabled = False
        self._update_status("Permissão necessária", error=True)

    def _init_camera(self):
        """Inicializa a câmera."""
        self._update_status("Iniciando câmera...")

        try:
            from kivy.uix.camera import Camera
            
            if self.camera_placeholder.parent:
                self.camera_container.remove_widget(self.camera_placeholder)

            self.camera = Camera(
                resolution=(1280, 720),
                play=True,
                index=0,
                allow_stretch=True,
                keep_ratio=True
            )
            
            self.camera_container.add_widget(self.camera, index=1)

            self.permission_btn.opacity = 0
            self.permission_btn.disabled = True

            self._update_status("Monitorando pista...")
            self._start_processing()

        except Exception as e:
            Logger.error(f"App: Erro ao iniciar câmera: {e}")
            self.camera_placeholder.text = f"Erro: {e}"
            self._update_status(f"Erro na câmera: {e}", error=True)

    def _start_processing(self):
        """Inicia processamento de frames."""
        if self.processing_event:
            return
        # 10 FPS para boa detecção sem drenar bateria
        self.processing_event = Clock.schedule_interval(self._process_frame, 1/10)
        Logger.info("App: Processamento de frames iniciado (10 FPS)")

    def _stop_processing(self):
        """Para processamento de frames."""
        if self.processing_event:
            self.processing_event.cancel()
            self.processing_event = None

    def _process_frame(self, dt):
        """Processa um frame da câmera."""
        if not self.camera or not self.camera.texture or not self.detector:
            return

        try:
            import numpy as np
            import cv2
            
            texture = self.camera.texture
            pixels = texture.pixels
            
            frame = np.frombuffer(pixels, dtype=np.uint8)
            frame = frame.reshape(texture.height, texture.width, 4)
            frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGBA2BGR)

            detections = self.detector.detect(frame_bgr)

            if detections:
                self._handle_detections(detections)
            else:
                self.alert_overlay.clear()
                if "Buraco" in self.status_label.text or "BURACO" in self.status_label.text:
                    self._update_status("Monitorando pista...")

        except Exception as e:
            Logger.error(f"App: Erro no processamento: {e}")

    def _handle_detections(self, detections):
        """Processa detecções encontradas."""
        self.alert_overlay.show_detections(detections, self.camera)

        now = datetime.now()
        should_alert = (
            self.last_alert_time is None or
            (now - self.last_alert_time).total_seconds() >= self.alert_cooldown
        )

        if should_alert:
            self.last_alert_time = now
            self.detection_count += len(detections)
            self.counter_label.text = f"Buracos detectados: {self.detection_count}"

            avg_conf = sum(d[4] for d in detections) / len(detections)
            self._update_status(
                f"⚠️ BURACO DETECTADO!\nConfiança: {avg_conf:.0%}",
                warning=True
            )
            
            self._vibrate()

    def _vibrate(self):
        """Vibra o dispositivo (Android)."""
        if not IS_ANDROID or not PythonActivity:
            return
        try:
            from jnius import autoclass
            Vibrator = autoclass('android.os.Vibrator')
            activity = PythonActivity.mActivity
            vibrator = activity.getSystemService(Context.VIBRATOR_SERVICE)
            if vibrator:
                vibrator.vibrate(500)
        except Exception as e:
            Logger.warning(f"App: Vibração falhou: {e}")

    def _update_status(self, text, error=False, warning=False):
        """Atualiza label de status."""
        if error:
            color = (1, 0.3, 0.3, 1)
        elif warning:
            color = (1, 0.6, 0, 1)
        else:
            color = (0.4, 1, 0.4, 1)

        self.status_label.text = f"[b]Detector de Buracos[/b]\n{text}"
        self.status_label.color = color


class PotholeDetectorApp(App):
    """Aplicativo principal."""

    def build(self):
        self.title = "Detector de Buracos"
        Window.clearcolor = (0.1, 0.1, 0.15, 1)
        return PotholeDetectorLayout()

    def on_pause(self):
        return True

    def on_resume(self):
        pass

    def on_stop(self):
        if hasattr(self.root, '_stop_processing'):
            self.root._stop_processing()


if __name__ == "__main__":
    PotholeDetectorApp().run()
