"""Aplicativo de detecção de buracos com câmera traseira e IA."""

from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

import cv2
import numpy as np
from kivy.app import App
from kivy.clock import Clock
from kivy.core.audio import SoundLoader
from kivy.graphics import Color, Line, Rectangle
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.camera import Camera
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.utils import platform

from detector import PotholeDetector

IS_ANDROID = platform == "android"

if IS_ANDROID:
    try:
        from android.permissions import Permission, check_permission, request_permissions
    except ImportError:  # Segurança extra quando rodando no desktop
        Permission = None
        check_permission = None
        request_permissions = None
else:
    Permission = None
    check_permission = None
    request_permissions = None


class DetectionOverlay(Widget):
    """Sobreposição que desenha alertas visuais sobre o feed da câmera."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._last_detections: List[Tuple[float, float, float, float, float]] = []
        self.bind(pos=self._redraw, size=self._redraw)

    def _redraw(self, *_):
        self.draw(self._last_detections)

    def clear(self) -> None:
        self.canvas.clear()
        self._last_detections = []

    def draw(self, detections: List[Tuple[float, float, float, float, float]]) -> None:
        self._last_detections = detections or []
        self.canvas.clear()
        if not detections:
            return

        with self.canvas:
            Color(1, 0, 0, 0.2)
            Rectangle(pos=self.pos, size=self.size)
            Color(1, 0, 0, 0.95)
            for x_norm, y_norm, w_norm, h_norm, _ in detections:
                w_px = max(w_norm * self.width, 2)
                h_px = max(h_norm * self.height, 2)
                x_px = self.x + x_norm * self.width
                y_px = self.y + (1 - (y_norm + h_norm)) * self.height
                Line(rectangle=(x_px, y_px, w_px, h_px), width=2)


class PotholeDetectionLayout(BoxLayout):
    """Layout principal que controla UI, câmera e IA."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.spacing = 8
        self.padding = 12

        self.detector = PotholeDetector(use_yolo=False)
        self.camera_widget: Optional[Camera] = None
        self.frame_event = None
        self.alert_overlay = DetectionOverlay(size_hint=(1, 1))
        self.pothole_count = 0
        self.last_alert_ts = None
        self.alert_cooldown = 2.0
        self.status_reset_event = None

        self.status_label = Label(
            text="Iniciando sensores...",
            size_hint=(1, 0.1),
            font_size="20sp",
            color=(0.7, 0.9, 1, 1)
        )
        self.counter_label = Label(
            text="Buracos detectados: 0",
            size_hint=(1, 0.08),
            font_size="16sp",
            color=(1, 1, 0.4, 1)
        )

        self.camera_container = FloatLayout(size_hint=(1, 0.72))
        self.camera_placeholder = Label(
            text="Preparando câmera...",
            halign="center",
            valign="middle"
        )
        self.camera_placeholder.bind(size=self._sync_placeholder_text)
        self.camera_container.add_widget(self.camera_placeholder)
        self.camera_container.add_widget(self.alert_overlay)

        self.permission_button = Button(
            text="Permitir acesso à câmera",
            size_hint=(1, 0.1),
            opacity=0,
            disabled=True,
            on_press=lambda *_: self._request_android_permissions()
        )

        self.add_widget(self.status_label)
        self.add_widget(self.counter_label)
        self.add_widget(self.camera_container)
        self.add_widget(self.permission_button)

        self.alert_sound = None
        self._load_alert_sound()

        if IS_ANDROID:
            Clock.schedule_once(lambda *_: self._request_android_permissions(), 0.5)
        else:
            Clock.schedule_once(lambda *_: self._init_camera(), 0.2)

    def _sync_placeholder_text(self, *_):
        self.camera_placeholder.text_size = self.camera_placeholder.size

    def _load_alert_sound(self) -> None:
        sound_path = Path("alert.wav")
        if sound_path.exists():
            self.alert_sound = SoundLoader.load(str(sound_path))

    def _request_android_permissions(self) -> None:
        if not IS_ANDROID or not Permission or not request_permissions:
            self._init_camera()
            return

        if check_permission and check_permission(Permission.CAMERA):
            self._init_camera()
            return

        perms = [Permission.CAMERA]
        if hasattr(Permission, "WRITE_EXTERNAL_STORAGE"):
            perms.append(Permission.WRITE_EXTERNAL_STORAGE)
        request_permissions(perms, self._on_permissions_result)
        self.status_label.text = "Solicitando acesso à câmera..."
        self.status_label.color = (1, 0.8, 0.2, 1)

    def _on_permissions_result(self, permissions, grant_results) -> None:
        granted = all(grant_results) if isinstance(grant_results, (list, tuple)) else bool(grant_results)
        if granted:
            self.permission_button.opacity = 0
            self.permission_button.disabled = True
            self._init_camera()
        else:
            self.camera_placeholder.text = (
                "❌ Permissão negada.\n"
                "Vá em Configurações > Apps > Detector de Buracos > Permissões > Câmera"
            )
            self.permission_button.opacity = 1
            self.permission_button.disabled = False
            self.status_label.text = "Permissão obrigatória para continuar"
            self.status_label.color = (1, 0.3, 0.3, 1)

    def _init_camera(self) -> None:
        if self.camera_widget:
            return

        try:
            self.camera_widget = Camera(
                resolution=(1280, 720),
                index=0,
                play=True,
                allow_stretch=True,
                keep_ratio=True
            )
            self.camera_container.remove_widget(self.camera_placeholder)
            self.camera_container.add_widget(self.camera_widget, index=0)
            self.status_label.text = "Monitorando pista..."
            self.status_label.color = (0.4, 1, 0.4, 1)
            self._start_processing()
        except Exception as exc:
            self.camera_placeholder.text = f"Erro ao iniciar câmera: {exc}"
            self.status_label.text = "Não foi possível acessar a câmera"
            self.status_label.color = (1, 0.3, 0.3, 1)

    def _start_processing(self) -> None:
        if self.frame_event is None:
            self.frame_event = Clock.schedule_interval(self._process_frame, 1 / 8.0)

    def _process_frame(self, _dt) -> None:
        if not self.camera_widget or not self.camera_widget.texture:
            return

        texture = self.camera_widget.texture
        frame = np.frombuffer(texture.pixels, dtype=np.uint8)
        frame = frame.reshape(texture.height, texture.width, 4)
        frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGBA2BGR)

        detections = self.detector.detect(frame_bgr)
        if detections:
            self._handle_detections(detections)
        else:
            self._clear_alert()

    def _handle_detections(self, detections: List[Tuple[float, float, float, float, float]]) -> None:
        self.alert_overlay.draw(detections)
        now = datetime.now()
        should_alert = True
        if self.last_alert_ts is not None:
            delta = (now - self.last_alert_ts).total_seconds()
            should_alert = delta >= self.alert_cooldown

        if not should_alert:
            return

        self.last_alert_ts = now
        self.pothole_count += len(detections)
        self.counter_label.text = f"Buracos detectados: {self.pothole_count}"

        avg_conf = sum(det[4] for det in detections) / len(detections)
        self.status_label.text = f"⚠️ Buraco detectado! Confiança {avg_conf:.0%}"
        self.status_label.color = (1, 0.4, 0.4, 1)

        if self.alert_sound:
            self.alert_sound.stop()
            self.alert_sound.play()

        if self.status_reset_event:
            self.status_reset_event.cancel()
        self.status_reset_event = Clock.schedule_once(lambda *_: self._reset_status(), 2.5)

    def _reset_status(self) -> None:
        self.status_label.text = "Monitorando pista..."
        self.status_label.color = (0.4, 1, 0.4, 1)

    def _clear_alert(self) -> None:
        self.alert_overlay.clear()
        if self.status_label.text.startswith("⚠️"):
            self._reset_status()


class PotholeDetectorApp(App):
    """App Kivy principal."""

    def build(self):
        self.title = "Detector de Buracos"
        return PotholeDetectionLayout()

    def on_pause(self):
        return True

    def on_resume(self):
        pass


if __name__ == "__main__":
    PotholeDetectorApp().run()
