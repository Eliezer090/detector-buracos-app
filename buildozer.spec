[app]

# Título do aplicativo
title = Detector de Buracos

# Nome do pacote
package.name = potholedetector

# Domínio do pacote
package.domain = org.detector.buracos

# Diretório do código fonte
source.dir = .

# Extensões a incluir
source.include_exts = py,png,jpg,kv,atlas,wav,mp3

# Versão
version = 1.0.4

# Requisitos com OpenCV para detecção de qualidade
requirements = python3,kivy==2.2.0,numpy,opencv,pillow,android,pyjnius

# Orientação
orientation = landscape

# Fullscreen
fullscreen = 1

# Permissões Android
android.permissions = android.permission.CAMERA,android.permission.VIBRATE,android.permission.WAKE_LOCK

# API Android
android.api = 33
android.minapi = 24
android.sdk = 33
android.ndk = 25b

# Armazenamento privado
android.private_storage = True

# Aceitar licenças automaticamente
android.accept_sdk_license = True

# Arquitetura - apenas arm64 para dispositivos modernos (menor APK)
android.archs = arm64-v8a

# Gradle e Java
android.gradle_dependencies = androidx.core:core:1.6.0
android.enable_androidx = True

# Bootstrap
p4a.bootstrap = sdl2

# Branch do python-for-android
p4a.branch = master

# Logs
log_level = 2

# Diretório de build
build_dir = .buildozer

# Limpeza
warn_on_root = 1

[buildozer]

# Nível de log
log_level = 2

# Aviso sobre root
warn_on_root = 1
