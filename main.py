"""
Detector de Buracos - Aplicativo Android
=========================================
Usa câmera traseira + IA para detectar buracos na pista em tempo real.
"""

import os
from datetime import datetime
from typing import List, Tuple
from collections import deque

# Kivy config DEVE vir antes de qualquer outro import do Kivy
os.environ.setdefault('KIVY_LOG_LEVEL', 'info')

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Line, Rectangle, PushMatrix, PopMatrix, Rotate
from kivy.graphics.texture import Texture
from kivy.logger import Logger
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
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


class DebugPanel(ScrollView):
    """Painel de debug com logs em tempo real."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (1, None)
        self.height = 150
        self.do_scroll_x = False
        self.bar_width = 10
        self.bar_color = (0.5, 0.5, 0.5, 0.8)
        
        self.log_label = Label(
            text="[DEBUG] Painel de logs\n",
            markup=True,
            size_hint_y=None,
            font_size="12sp",
            halign="left",
            valign="top",
            color=(0.8, 1, 0.8, 1)
        )
        self.log_label.bind(texture_size=self._update_height)
        self.log_label.bind(width=lambda *_: setattr(self.log_label, 'text_size', (self.log_label.width, None)))
        
        self.add_widget(self.log_label)
        
        # Histórico de logs (máximo 50 linhas)
        self.log_history = deque(maxlen=50)
        
    def _update_height(self, *_):
        self.log_label.height = max(self.log_label.texture_size[1], self.height)
        # Auto-scroll para o final
        self.scroll_y = 0
        
    def add_log(self, message: str, level: str = "INFO"):
        """Adiciona uma linha de log."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        if level == "DETECT":
            color = "[color=ff9900]"  # Laranja
        elif level == "ALERT":
            color = "[color=ff0000]"  # Vermelho
        elif level == "OK":
            color = "[color=00ff00]"  # Verde
        else:
            color = "[color=aaaaaa]"  # Cinza
            
        log_line = f"{color}[{timestamp}] {message}[/color]"
        self.log_history.append(log_line)
        
        self.log_label.text = "\n".join(self.log_history)


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
        self.debug_enabled = False
        self.frame_count = 0
        self.last_fps_time = datetime.now()
        self.current_fps = 0
        self.rotation_mode = 0  # 0=nenhuma, 1=90°, 2=180°, 3=270°

        # UI Components
        self.status_label = Label(
            text="[b]Detector de Buracos[/b]\nIniciando...",
            markup=True,
            size_hint=(1, None),
            height=60,
            font_size="18sp",
            halign="center",
            valign="middle"
        )
        self.status_label.bind(size=lambda *_: setattr(
            self.status_label, 'text_size', self.status_label.size))

        self.counter_label = Label(
            text="Buracos detectados: 0",
            size_hint=(1, None),
            height=30,
            font_size="16sp",
            color=(1, 1, 0, 1)
        )

        # Container para câmera
        self.camera_container = FloatLayout(size_hint=(1, 1))
        self.camera_placeholder = Label(
            text="Aguardando permissão da câmera...",
            halign="center"
        )
        self.camera_container.add_widget(self.camera_placeholder)

        # Overlay para detecções
        self.alert_overlay = AlertOverlay()
        self.camera_container.add_widget(self.alert_overlay)

        # Painel de Debug (inicialmente oculto)
        self.debug_panel = DebugPanel()
        self.debug_panel.opacity = 0
        self.debug_panel.height = 0

        # Botão de Debug
        self.debug_btn = Button(
            text="📊 Debug",
            size_hint=(0.33, None),
            height=40,
            background_color=(0.3, 0.3, 0.5, 1)
        )
        self.debug_btn.bind(on_press=self._toggle_debug)

        # Botão de Rotação
        self.rotate_btn = Button(
            text="🔄 Rotação: 0°",
            size_hint=(0.33, None),
            height=40,
            background_color=(0.3, 0.5, 0.3, 1)
        )
        self.rotate_btn.bind(on_press=self._toggle_rotation)

        # Container para botões
        self.buttons_container = BoxLayout(
            orientation='horizontal',
            size_hint=(1, None),
            height=40,
            spacing=5
        )
        self.buttons_container.add_widget(self.debug_btn)
        self.buttons_container.add_widget(self.rotate_btn)

        # Botão de permissão (inicialmente oculto)
        self.permission_btn = Button(
            text="Permitir Câmera",
            size_hint=(1, None),
            height=50,
            opacity=0,
            disabled=True
        )
        self.permission_btn.bind(on_press=lambda *_: self._request_permissions())

        # Montar layout
        self.add_widget(self.status_label)
        self.add_widget(self.counter_label)
        self.add_widget(self.buttons_container)
        self.add_widget(self.debug_panel)
        self.add_widget(self.camera_container)
        self.add_widget(self.permission_btn)

        # Inicialização
        Clock.schedule_once(self._initialize, 0.5)

    def _toggle_debug(self, *_):
        """Liga/desliga o painel de debug."""
        self.debug_enabled = not self.debug_enabled
        
        if self.debug_enabled:
            self.debug_panel.opacity = 1
            self.debug_panel.height = 150
            self.debug_btn.text = "📊 Ocultar"
            self.debug_btn.background_color = (0.5, 0.3, 0.3, 1)
            self._log("Painel de debug ativado", "OK")
            self._log(f"Detector: {type(self.detector).__name__ if self.detector else 'Não inicializado'}", "INFO")
            self._log(f"Rotação atual: {self.rotation_mode * 90}°", "INFO")
        else:
            self.debug_panel.opacity = 0
            self.debug_panel.height = 0
            self.debug_btn.text = "📊 Debug"
            self.debug_btn.background_color = (0.3, 0.3, 0.5, 1)

    def _toggle_rotation(self, *_):
        """Alterna entre os modos de rotação da câmera."""
        self.rotation_mode = (self.rotation_mode + 1) % 4
        rotation_degrees = self.rotation_mode * 90
        self.rotate_btn.text = f"🔄 Rotação: {rotation_degrees}°"
        self._log(f"Rotação alterada para {rotation_degrees}°", "OK")

    def _log(self, message: str, level: str = "INFO"):
        """Adiciona log ao painel de debug."""
        if self.debug_enabled:
            self.debug_panel.add_log(message, level)

    def _initialize(self, *_):
        """Inicializa detector e solicita permissões."""
        try:
            from detector import PotholeDetector
            self.detector = PotholeDetector()
            Logger.info("App: Detector inicializado com sucesso")
            self._log(f"Detector carregado: {self.detector.detector_name}", "OK")
        except Exception as e:
            Logger.error(f"App: Erro ao inicializar detector: {e}")
            self._update_status(f"Erro: {e}", error=True)
            self._log(f"Erro ao carregar detector: {e}", "ALERT")
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
        self._log("Permissão de câmera negada", "ALERT")

    def _init_camera(self):
        """Inicializa a câmera com tratamento robusto de erros."""
        self._update_status("Iniciando câmera...")
        self._log("Inicializando câmera...", "INFO")

        # Tentar múltiplas configurações de câmera
        camera_configs = [
            {"resolution": (640, 480), "index": 0},   # Baixa resolução, câmera 0
            {"resolution": (1280, 720), "index": 0},  # HD, câmera 0
            {"resolution": (640, 480), "index": 1},   # Baixa resolução, câmera 1
            {"resolution": (320, 240), "index": 0},   # Muito baixa, câmera 0
        ]
        
        for i, config in enumerate(camera_configs):
            try:
                self._log(f"Tentativa {i+1}: res={config['resolution']}, cam={config['index']}", "INFO")
                self._try_init_camera(config["resolution"], config["index"])
                return  # Sucesso!
            except Exception as e:
                error_msg = str(e)
                self._log(f"Falha tentativa {i+1}: {error_msg[:50]}", "ALERT")
                Logger.warning(f"App: Câmera config {i+1} falhou: {e}")
                continue
        
        # Todas as tentativas falharam
        self._log("ERRO: Todas as configurações de câmera falharam!", "ALERT")
        self._show_camera_error("Não foi possível iniciar a câmera.\nTente reiniciar o app.")

    def _try_init_camera(self, resolution, index):
        """Tenta inicializar a câmera com uma configuração específica."""
        from kivy.uix.camera import Camera
        
        if self.camera_placeholder.parent:
            self.camera_container.remove_widget(self.camera_placeholder)
        
        # Remove câmera anterior se existir
        if self.camera and self.camera.parent:
            self.camera_container.remove_widget(self.camera)
            self.camera = None

        self.camera = Camera(
            resolution=resolution,
            play=False,  # Inicia pausado para evitar erro
            index=index,
            allow_stretch=True,
            keep_ratio=True
        )
        
        self.camera_container.add_widget(self.camera, index=1)
        
        # Agendar início com delay para estabilizar
        def start_camera(*_):
            try:
                self.camera.play = True
                self._log(f"Câmera iniciada: {resolution[0]}x{resolution[1]}", "OK")
                self._update_status("Monitorando pista...")
                self.permission_btn.opacity = 0
                self.permission_btn.disabled = True
                self._start_processing()
            except Exception as e:
                self._log(f"Erro ao iniciar play: {e}", "ALERT")
                raise e
        
        Clock.schedule_once(start_camera, 0.5)

    def _show_camera_error(self, message):
        """Mostra erro de câmera na interface."""
        if self.camera_placeholder.parent is None:
            self.camera_container.add_widget(self.camera_placeholder)
        self.camera_placeholder.text = f"❌ Erro de Câmera\n\n{message}"
        self._update_status("Erro na câmera", error=True)

    def _start_processing(self):
        """Inicia processamento de frames."""
        if self.processing_event:
            return
        # Aguardar câmera estabilizar antes de processar
        Clock.schedule_once(self._delayed_start_processing, 1.0)

    def _delayed_start_processing(self, *_):
        """Inicia processamento após delay."""
        if self.processing_event:
            return
        # 5 FPS para boa detecção sem drenar bateria e evitar erros
        self.processing_event = Clock.schedule_interval(self._process_frame, 1/5)
        Logger.info("App: Processamento de frames iniciado (5 FPS)")
        self._log("Processamento iniciado (5 FPS)", "OK")
        self.consecutive_errors = 0

    def _stop_processing(self):
        """Para processamento de frames."""
        if self.processing_event:
            self.processing_event.cancel()
            self.processing_event = None
            self._log("Processamento parado", "INFO")

    def _process_frame(self, dt):
        """Processa um frame da câmera."""
        # Verificações de segurança
        if not self.camera:
            return
        
        if not self.camera.play:
            return
            
        if not self.camera.texture:
            if self.debug_enabled:
                self._log("Aguardando texture da câmera...", "INFO")
            return
            
        if not self.detector:
            return

        try:
            import numpy as np
            import cv2
            
            # Calcular FPS
            self.frame_count += 1
            now = datetime.now()
            elapsed = (now - self.last_fps_time).total_seconds()
            if elapsed >= 1.0:
                self.current_fps = self.frame_count / elapsed
                self.frame_count = 0
                self.last_fps_time = now
                if self.debug_enabled:
                    self._log(f"FPS: {self.current_fps:.1f} | Frames OK", "INFO")
            
            texture = self.camera.texture
            
            # Verificar se pixels estão disponíveis
            if texture.pixels is None:
                return
                
            pixels = texture.pixels
            
            # Verificar tamanho esperado
            expected_size = texture.height * texture.width * 4
            if len(pixels) != expected_size:
                if self.debug_enabled:
                    self._log(f"Tamanho pixels incorreto: {len(pixels)} != {expected_size}", "ALERT")
                return
            
            frame = np.frombuffer(pixels, dtype=np.uint8)
            frame = frame.reshape(texture.height, texture.width, 4)
            frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGBA2BGR)
            
            # Aplicar rotação conforme configuração do usuário
            if self.rotation_mode == 1:  # 90°
                frame_bgr = cv2.rotate(frame_bgr, cv2.ROTATE_90_CLOCKWISE)
            elif self.rotation_mode == 2:  # 180°
                frame_bgr = cv2.rotate(frame_bgr, cv2.ROTATE_180)
            elif self.rotation_mode == 3:  # 270°
                frame_bgr = cv2.rotate(frame_bgr, cv2.ROTATE_90_COUNTERCLOCKWISE)
            # rotation_mode == 0: sem rotação

            detections = self.detector.detect(frame_bgr)
            
            # Resetar contador de erros após sucesso
            self.consecutive_errors = 0
            
            # Log de debug sobre detecção
            if self.debug_enabled and self.frame_count % 5 == 0:  # Log a cada 5 frames
                if detections:
                    self._log(f"Detectando: {len(detections)} objeto(s)", "DETECT")

            if detections:
                self._handle_detections(detections)
            else:
                self.alert_overlay.clear()
                if "Buraco" in self.status_label.text or "BURACO" in self.status_label.text:
                    self._update_status("Monitorando pista...")

        except Exception as e:
            self.consecutive_errors = getattr(self, 'consecutive_errors', 0) + 1
            error_msg = str(e)[:60]
            Logger.error(f"App: Erro no processamento: {e}")
            
            if self.debug_enabled:
                self._log(f"Erro #{self.consecutive_errors}: {error_msg}", "ALERT")
            
            # Se muitos erros consecutivos, parar e reiniciar
            if self.consecutive_errors >= 10:
                self._log("Muitos erros! Reiniciando câmera...", "ALERT")
                self._stop_processing()
                Clock.schedule_once(lambda *_: self._init_camera(), 2.0)

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
            
            # Log detalhado de detecção
            for i, (x, y, w, h, conf) in enumerate(detections):
                self._log(f"Buraco #{i+1}: conf={conf:.0%} pos=({x:.2f},{y:.2f})", "ALERT")
            
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
