import streamlit as st
import cv2
import numpy as np
from PIL import Image

st.set_page_config(page_title="BioSolo Monitor", page_icon="🌱", layout="centered")

st.title("🌱 BioSolo Monitor v1.0")
st.write("Abra a câmera, alinhe o cartão de calibração e tire a foto para analisar a biologia do solo.")

# 1. Ativa o componente de câmera nativo do celular
foto_capturada = st.camera_input("Tirar foto do cartão")

if foto_capturada is not None:
    # Converter a imagem capturada para o formato OpenCV (BGR)
    imagem_pil = Image.open(foto_capturada)
    imagem_np = np.array(imagem_pil)
    # Streamlit lê em RGB, OpenCV trabalha em BGR
    img = cv2.cvtColor(imagem_np, cv2.COLOR_RGB2BGR)
    
    st.info("Processando imagem e aplicando normalização de luz...")
    
    try:
        # 2. Resolução padrão para retificar o cartão (600x600 pixels)
        tamanho_final = 600
        
        # --- PROTÓTIPO DE DETEÇÃO AUTOMÁTICA ---
        # Para fins de teste inicial sem os marcadores ArUco físicos impressos,
        # simulamos que o usuário centralizou bem o cartão na tela do celular.
        h, w, _ = img.shape
        pontos_origem = np.float32([[0, 0], [w, 0], [0, h], [w, h]])
        pontos_destino = np.float32([[0, 0], [tamanho_final, 0], [0, tamanho_final], [tamanho_final, tamanho_final]])
        
        # Alinha e recorta o cartão de forma estática
        matriz = cv2.getPerspectiveTransform(pontos_origem, pontos_destino)
        cartao = cv2.warpPerspective(img, matriz, (tamanho_final, tamanho_final))
        
        # 3. Mapeamento das Regiões de Interesse (ROIs) conforme o gabarito visual
        # Coordenadas baseadas em um cartão padrão centralizado de 600x600 pixels
        roi_preto   = cartao[50:120,  265:335]   # Topo
        roi_branco  = cartao[480:550, 265:335]   # Base
        roi_amostra = cartao[265:335, 265:335]   # Centro (Mancha Biológica)
        
        # 4. Extração dos canais de cores (Média BGR)
        m_preto = cv2.mean(roi_preto)[:3]
        m_branco = cv2.mean(roi_branco)[:3]
        m_amostra = cv2.mean(roi_amostra)[:3]
        
        # 5. Algoritmo de Calibração Matemática (Anulação de Sol / Sombra)
        # Processando canal por canal para evitar divisões por zero
        canais_corrigidos = []
        for i in range(3): # 0=B, 1=G, 2=R
            denominador = (m_branco[i] - m_preto[i])
            if denominador == 0: denominador = 1 # Evita erro matemático
            
            valor_normalizado = (m_amostra[i] - m_preto[i]) / denominador
            # Limita o resultado estritamente entre 0.0 e 1.0
            valor_normalizado = max(0.0, min(1.0, valor_normalizado))
            canais_corrigidos.append(valor_normalizado)
            
        # Transformando em escala de cinza biológica (Refletância Média)
        indice_biomassa = 1.0 - np.mean(canais_corrigidos)
        
        # 6. Exibição dos resultados na interface do celular
        st.success("Análise concluída com sucesso!")
        
        col1, col2 = st.columns(2)
        with col1:
            # Mostra o cartão recortado e processado pelo algoritmo
            cartao_rgb = cv2.cvtColor(cartao, cv2.COLOR_BGR2RGB)
            st.image(cartao_rgb, caption="Cartão Alinhado", use_column_width=True)
            
        with col2:
            st.metric(label="Índice de Biomassa Ativa", value=f"{indice_biomassa:.2f}")
            
            # Gráfico de diagnóstico provisório
            if indice_biomassa < 0.3:
                st.warning("Solo Degradado: Baixa atividade microbiológica. Adicione matéria orgânica ou bioestimulantes.")
            elif 0.3 <= indice_biomassa < 0.7:
                st.info("Solo Equilibrado: Atividade biológica moderada. Adequado para hortaliças gerais.")
            else:
                st.success("Solo Excelente: Altíssima atividade biológica e saúde do ecossistema de raízes.")
                
    except Exception as e:
        st.error(f"Erro ao processar o cartão. Certifique-se de enquadrar todo o gabarito. Detalhes: {e}")

