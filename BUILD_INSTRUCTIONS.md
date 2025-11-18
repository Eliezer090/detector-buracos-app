# 📦 Instruções de Build - Detector de Buracos

## ⚠️ Problemas Comuns Resolvidos

O buildozer é complexo e tem vários problemas no Windows/WSL. Aqui está o método CORRETO:

## 🔧 Método 1: Build Simplificado (RECOMENDADO)

### Passo 1: Preparar Ambiente Linux (WSL)

```bash
# No WSL Ubuntu, instale dependências básicas
sudo apt update
sudo apt install -y git zip unzip openjdk-17-jdk wget
sudo apt install -y python3.10 python3.10-venv python3.10-dev
sudo apt install -y build-essential libssl-dev libffi-dev
sudo apt install -y autoconf libtool pkg-config zlib1g-dev
sudo apt install -y libncurses-dev cmake
```

### Passo 2: Criar Ambiente Virtual com Python 3.10

```bash
# Python 3.10 é mais estável com buildozer
python3.10 -m venv ~/buildozer-venv
source ~/buildozer-venv/bin/activate

# Atualizar pip
pip install --upgrade pip setuptools wheel
```

### Passo 3: Instalar Buildozer

```bash
# Instalar buildozer
pip install buildozer==1.5.0
pip install cython==0.29.33

# Verificar instalação
buildozer --version
```

### Passo 4: Build da Versão Simples (Teste)

```bash
# Ir para o projeto
cd /mnt/c/Users/es19237/Desktop/AreaTrabalho/Python/AppViewBurracos

# Renomear main.py original
mv main.py main_full.py

# Usar versão simplificada
cp main_simple.py main.py

# Limpar builds anteriores
rm -rf .buildozer

# Fazer primeiro build (versão simples sem OpenCV)
buildozer -v android debug
```

**⏰ IMPORTANTE**: O primeiro build demora 40-90 minutos e baixa ~3GB de dados (Android SDK/NDK).

### Passo 5: Testar APK

```bash
# APK estará em:
ls -lh bin/*.apk

# Transferir para o celular via Windows:
# O arquivo estará em: C:\Users\es19237\Desktop\AreaTrabalho\Python\AppViewBurracos\bin\
# Copie para o celular via cabo USB ou Google Drive
```

### Passo 6: Build Versão Completa (Com AI)

Depois que a versão simples funcionar, compile a versão com OpenCV:

```bash
# Voltar para versão completa
mv main.py main_simple_backup.py
mv main_full.py main.py

# Editar buildozer.spec - adicionar opencv
# Mudar linha: requirements = python3,kivy==2.2.0,pillow,android
# Para: requirements = python3,kivy==2.2.0,opencv,numpy,pillow,android

# Build novamente
buildozer android debug
```

---

## 🐳 Método 2: Usar Docker (Alternativa)

Se o método acima falhar, use Docker:

```bash
# No Windows PowerShell
cd C:\Users\es19237\Desktop\AreaTrabalho\Python\AppViewBurracos

# Criar container buildozer
docker run --rm -v ${PWD}:/app kivy/buildozer android debug
```

---

## ☁️ Método 3: GitHub Actions (Mais Fácil)

Deixe o GitHub compilar para você:

1. **Criar repositório no GitHub**
2. **Fazer upload dos arquivos**
3. **Criar arquivo `.github/workflows/build.yml`**:

```yaml
name: Build Android APK

on:
  push:
    branches: [ main ]
  workflow_dispatch:

jobs:
  build:
    runs-on: ubuntu-20.04
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Setup Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.10'
    
    - name: Install Buildozer
      run: |
        pip install buildozer==1.5.0 cython==0.29.33
    
    - name: Build APK
      run: |
        cp main_simple.py main.py
        buildozer android debug
    
    - name: Upload APK
      uses: actions/upload-artifact@v3
      with:
        name: pothole-detector-apk
        path: bin/*.apk
```

4. **Commit e push** - O GitHub compila automaticamente
5. **Baixe o APK** da aba "Actions" do seu repositório

---

## 📱 Método 4: Usar Kivy Launcher (Teste Rápido)

Para testes imediatos SEM compilar:

1. Instale **Kivy Launcher** no celular (Google Play Store)
2. Crie pasta no celular: `/sdcard/kivy/potholedetector/`
3. Copie os arquivos: `main_simple.py` → renomeie para `main.py`
4. Abra pelo Kivy Launcher

---

## 🔍 Solução de Problemas

### Erro: "distutils not found"
```bash
pip install setuptools --force-reinstall
```

### Erro: "Cython not found"
```bash
pip install cython==0.29.33
```

### Erro: "Java not found"
```bash
sudo apt install -y openjdk-17-jdk
export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
```

### Build muito lento
```bash
# Usar menos threads se o WSL estiver lento
buildozer android debug 2>&1 | tee build.log
```

### Limpar tudo e recomeçar
```bash
rm -rf .buildozer
rm -rf bin
buildozer android clean
```

---

## ✅ Checklist de Build Bem-sucedido

- [ ] WSL Ubuntu instalado e atualizado
- [ ] Python 3.10 instalado
- [ ] Ambiente virtual criado e ativado
- [ ] Buildozer 1.5.0 instalado
- [ ] Java JDK 17 instalado
- [ ] Versão simples do app testada primeiro
- [ ] Build completo sem erros
- [ ] APK gerado em `bin/`
- [ ] APK instalado e testado no celular

---

## 📚 Recursos Úteis

- [Documentação Buildozer](https://buildozer.readthedocs.io/)
- [Kivy Android](https://kivy.org/doc/stable/guide/packaging-android.html)
- [Python-for-Android](https://python-for-android.readthedocs.io/)

---

**Recomendação**: Use o **Método 3 (GitHub Actions)** se estiver com problemas no WSL. É mais simples e confiável!
