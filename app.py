import streamlit as st
import cv2
import numpy as np
from PIL import Image

st.set_page_config(page_title="BioSolo Monitor", page_icon="🌱", layout="centered")

st.title("🌱 BioSolo Monitor v1.1")
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
        
        # =========================================================================
        # 5. NOVO BLOCO: ALGORITMO DE CALIBRAÇÃO E SEPARAÇÃO DE FUNGOS/BACTÉRIAS
        # =========================================================================
        
        # No OpenCV, as médias são extraídas na ordem BGR (0=Azul, 1=Verde, 2=Vermelho)
        # Aplicamos a normalização individual para cada canal (evitando divisão por zero)
        den_b = (m_branco[0] - m_preto[0])
        den_g = (m_branco[1] - m_preto[1])
        den_r = (m_branco[2] - m_preto[2])
        
        b_norm = (m_amostra[0] - m_preto[0]) / (den_b if den_b != 0 else 1)
        g_norm = (m_amostra[1] - m_preto[1]) / (den_g if den_g != 0 else 1)
        r_norm = (m_amostra[2] - m_preto[2]) / (den_r if den_r != 0 else 1)
        
        # Limitar os valores estritamente entre 0.0 e 1.0
        b_norm = max(0.0, min(1.0, b_norm))
        g_norm = max(0.0, min(1.0, g_norm))
        r_norm = max(0.0, min(1.0, r_norm))
        
        # 5.1 Cálculo da Biomassa Total Corrigida (usando o canal verde como referência)
        biomassa_total = 1.0 - g_norm  
        
        # 5.2 Relação Fungo/Bactéria (F:B) baseada na assinatura de cor (absorção do azul)
        if b_norm == 0: b_norm = 0.001  
        relacao_fb = r_norm / b_norm
        
        # 5.3 Separando as populações em porcentagem (Estimativa Matemática)
        porcentagem_fungos = (relacao_fb / (relacao_fb + 1.0)) * 100
        porcentagem_bacterias = 100 - porcentagem_fungos
        
        # =========================================================================
        
        # 6. Exibição dos resultados na interface do celular
        st.success("Análise concluída com sucesso!")
        
        col1, col2 = st.columns(2)
        with col1:
            # Mostra o cartão recortado e processado pelo algoritmo
            cartao_rgb = cv2.cvtColor(cartao, cv2.COLOR_BGR2RGB)
            st.image(cartao_rgb, caption="Cartão Alinhado", use_column_width=True)
            
        with col2:
            st.metric(label="Biomassa Microbiana Total", value=f"{biomassa_total:.2f}")
            st.metric(label="Relação Fungo : Bactéria (F:B)", value=f"{relacao_fb:.2f}")
            
            st.write(f"📊 **Composição Estimada:**")
            st.progress(int(porcentagem_fungos), text=f"Fungos: {porcentagem_fungos:.1f}%")
            st.progress(int(porcentagem_bacterias), text=f"Bactérias: {porcentagem_bacterias:.1f}%")
            
            # Diagnóstico baseado no perfil do solo
            st.write("---")
            if biomassa_total < 0.3:
                st.warning("⚠️ **Solo Frágil:** Baixa atividade biológica geral. Recomenda-se adicionar matéria orgânica.")
            elif relacao_fb < 0.5:
                st.info("🥦 **Solo Bacteriano:** Excelente para hortaliças foliares de ciclo rápido (alface, rúcula, couve).")
            elif 0.5 <= relacao_fb <= 1.5:
                st.success("🍅 **Solo Equilibrado:** Ótimo para frutos e grãos (tomate, pimentão, feijão).")
            else:
                st.info("🌲 **Solo Fúngico:** Perfil de sistemas florestais, pomares ou plantio direto muito antigo.")
                
    except Exception as e:
        st.error(f"Erro ao processar o cartão. Certifique-se de enquadrar todo o gabarito. Detalhes: {e}")
