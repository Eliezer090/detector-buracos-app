# 🚀 Como Fazer Build no GitHub Actions

## 📋 Passos para Compilar seu APK no GitHub (Grátis e Automático)

### 1️⃣ Criar Repositório no GitHub

1. Acesse [github.com](https://github.com) e faça login
2. Clique em **"New repository"** (botão verde)
3. Nomeie como: `detector-buracos-app`
4. Escolha **Public** (para usar Actions grátis)
5. **NÃO** marque "Initialize with README"
6. Clique em **"Create repository"**

### 2️⃣ Preparar os Arquivos Localmente

No Windows PowerShell:

```powershell
cd C:\Users\es19237\Desktop\AreaTrabalho\Python\AppViewBurracos

# Inicializar Git (se ainda não tiver)
git init

# Adicionar todos os arquivos
git add .

# Fazer primeiro commit
git commit -m "Initial commit - Detector de Buracos App"

# Conectar ao repositório remoto (substitua SEU_USUARIO pelo seu usuário GitHub)
git remote add origin https://github.com/SEU_USUARIO/detector-buracos-app.git

# Enviar para o GitHub
git branch -M main
git push -u origin main
```

### 3️⃣ O GitHub Vai Compilar Automaticamente

Após o `git push`:

1. Acesse seu repositório no GitHub
2. Clique na aba **"Actions"** (no topo)
3. Você verá o workflow **"Build Android APK"** rodando
4. Aguarde 20-40 minutos (primeira vez demora mais)
5. ✅ Quando ficar verde, clique no workflow
6. Role até **"Artifacts"** no final da página
7. Baixe **"pothole-detector-apk-debug"**
8. Descompacte o ZIP e instale o APK no celular

### 4️⃣ Atualizações Futuras

Sempre que você modificar o código:

```powershell
cd C:\Users\es19237\Desktop\AreaTrabalho\Python\AppViewBurracos

git add .
git commit -m "Descrição da mudança"
git push
```

O GitHub automaticamente compila uma nova versão!

---

## 📱 Instalar APK no Celular

### Android:

1. Baixe o APK do GitHub Actions
2. Transfira para o celular (cabo USB, Google Drive, etc)
3. No celular, vá em **Configurações** → **Segurança**
4. Ative **"Fontes desconhecidas"** ou **"Instalar apps desconhecidos"**
5. Abra o APK pelo gerenciador de arquivos
6. Clique em **"Instalar"**
7. Permita acesso à câmera quando solicitado

---

## 🔧 Troubleshooting

### ❌ Build Falhou?

1. Clique no workflow com erro
2. Clique em **"build"** para ver os logs
3. Procure por erros em vermelho
4. Baixe os logs de erro em **"Artifacts"** → **"buildozer-logs"**

### ⚠️ Problemas Comuns:

**Erro: "No module named 'detector'"**
- Solução: Use a versão simplificada (`main_simple.py`) primeiro

**Erro: "OpenCV recipe not found"**
- Solução: O `buildozer.spec` já está configurado com versão simplificada

**Build muito lento**
- Normal na primeira vez (~40 min)
- Builds seguintes são mais rápidos (~15-20 min) por causa do cache

---

## 💡 Dicas

- ✅ Use **branches** para testar mudanças sem quebrar a versão principal
- ✅ O cache do GitHub acelera builds futuros
- ✅ Você tem 2000 minutos grátis/mês de Actions
- ✅ Se o build falhar, você não gasta minutos

---

## 🎯 Próximos Passos

Depois que o build simples funcionar:

1. Teste o APK no celular
2. Verifique se a câmera funciona
3. Teste o botão de simulação
4. Se tudo OK, faça build da versão completa com AI:
   - Edite `buildozer.spec`
   - Mude `requirements` para incluir `opencv,numpy`
   - Use `main.py` original (com detector.py)
   - Commit e push

---

## 📞 Precisa de Ajuda?

- Confira os logs completos no GitHub Actions
- Verifique se todos os arquivos foram commitados
- Certifique-se de que `.github/workflows/build.yml` existe

**Boa sorte! 🚀**
