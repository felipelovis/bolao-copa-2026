import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

# Configuração da página
st.set_page_config(
    page_title="Bolão Copa do Mundo 2026",
    page_icon="⚽",
    layout="wide"
)

# ==================== CONFIGURAÇÕES DE SEGURANÇA ====================

# DATAS LIMITE por fase (AJUSTE AQUI!)
DATAS_LIMITE = {
    'Grupo': datetime(2026, 6, 11, 14, 0),
    '16 avos': datetime(2025, 11, 12, 12, 0),
    'Oitavas de final': datetime(2025, 11, 12, 12, 0),
    'Quartas de final': datetime(2025, 11, 12, 16, 0),
    'Semifinais': datetime(2025, 11, 12, 16, 0),
    'Terceiro e Quarto': datetime(2025, 11, 12, 14, 0),
    'Final': datetime(2025, 11, 12, 16, 0),
}

# CÓDIGOS DOS PARTICIPANTES (AJUSTE AQUI!)
PARTICIPANTES = {
    "Felipe": "ABC123",
    "João": "XYZ789",
    "Maria": "QWE456",
    "Pedro": "ASD321",
}

# NOME DO GOOGLE SHEETS (AJUSTE para o nome da sua planilha!)
NOME_PLANILHA = "Bolão Copa 2026"

# ====================================================================

# CSS customizado
st.markdown("""
    <style>
    .main { padding: 2rem; }
    .stButton>button {
        width: 100%;
        background-color: #4CAF50;
        color: white;
        height: 3em;
        font-size: 18px;
        font-weight: bold;
        border-radius: 10px;
    }
    .stButton>button:hover { background-color: #45a049; }
    .jogo-card {
        background-color: #f0f2f6;
        padding: 1.5rem;
        border-radius: 10px;
        margin-bottom: 1rem;
        border: 2px solid #e0e0e0;
    }
    .header-title {
        text-align: center;
        color: #1f77b4;
        font-size: 3rem;
        font-weight: bold;
    }
    .fase-bloqueada {
        background-color: #ffebee;
        border: 2px solid #ef5350;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    </style>
    """, unsafe_allow_html=True)

# Conectar ao Google Sheets
@st.cache_resource
def conectar_google_sheets():
    """Conecta ao Google Sheets usando credenciais do Streamlit secrets"""
    try:
        # Escopos necessários
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        
        # Credenciais dos secrets
        creds = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=scopes
        )
        
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        st.error(f"❌ Erro ao conectar Google Sheets: {e}")
        return None

# Função para verificar se fase está dentro do prazo
def fase_dentro_do_prazo(fase):
    if fase not in DATAS_LIMITE:
        return True
    return datetime.now() < DATAS_LIMITE[fase]

# Função para formatar tempo restante
def tempo_restante(fase):
    if fase not in DATAS_LIMITE:
        return "Sem prazo"
    
    if fase_dentro_do_prazo(fase):
        delta = DATAS_LIMITE[fase] - datetime.now()
        dias = delta.days
        horas = delta.seconds // 3600
        minutos = (delta.seconds % 3600) // 60
        
        if dias > 0:
            return f"{dias}d {horas}h {minutos}min"
        elif horas > 0:
            return f"{horas}h {minutos}min"
        else:
            return f"{minutos}min"
    return "indisponível"

# Função para validar participante
def validar_participante(nome, codigo):
    return nome in PARTICIPANTES and PARTICIPANTES[nome] == codigo

# Carregar jogos do Google Sheets
@st.cache_data(ttl=300)  # Cache por 5 minutos
def carregar_jogos():
    try:
        client = conectar_google_sheets()
        if client is None:
            return None
        
        planilha = client.open(NOME_PLANILHA)
        aba_jogos = planilha.worksheet("JOGOS")
        
        # Converter para DataFrame
        dados = aba_jogos.get_all_values()
        df = pd.DataFrame(dados[1:], columns=dados[0])
        
        return df
    except Exception as e:
        st.error(f"❌ Erro ao carregar jogos: {e}")
        return None

# Carregar palpites existentes
@st.cache_data(ttl=60)  # Cache por 1 minuto
def carregar_palpites_existentes():
    try:
        client = conectar_google_sheets()
        if client is None:
            return pd.DataFrame()
        
        planilha = client.open(NOME_PLANILHA)
        
        try:
            aba_palpites = planilha.worksheet("PALPITES")
            dados = aba_palpites.get_all_values()
            
            if len(dados) > 1:
                df = pd.DataFrame(dados[1:], columns=dados[0])
                return df
        except:
            # Se não existir a aba PALPITES, cria
            aba_palpites = planilha.add_worksheet(title="PALPITES", rows=1000, cols=10)
            aba_palpites.append_row(['Participante', 'id_jogo', 'PalpiteA', 'PalpiteB', 'GolsA', 'GolsB', 'Validade', 'Pontos'])
        
        return pd.DataFrame()
    except Exception as e:
        st.error(f"❌ Erro ao carregar palpites: {e}")
        return pd.DataFrame()

# Salvar palpites no Google Sheets
def salvar_palpites(nome, palpites_dict):
    try:
        client = conectar_google_sheets()
        if client is None:
            return False
        
        planilha = client.open(NOME_PLANILHA)
        aba_palpites = planilha.worksheet("PALPITES")
        
        # Carregar palpites existentes
        dados_existentes = aba_palpites.get_all_values()
        
        # Remover palpites antigos deste participante
        novos_dados = [dados_existentes[0]]  # Header
        for linha in dados_existentes[1:]:
            if linha[0] != nome:  # Coluna Participante
                novos_dados.append(linha)
        
        # Adicionar novos palpites
        for id_jogo in range(1, 105):
            if id_jogo in palpites_dict:
                palpite = palpites_dict[id_jogo]
                novos_dados.append([
                    nome,
                    str(id_jogo),
                    str(palpite['golsA']),
                    str(palpite['golsB']),
                    '',  # GolsA
                    '',  # GolsB
                    '',  # Validade
                    ''   # Pontos
                ])
        
        # Limpar e reescrever
        aba_palpites.clear()
        aba_palpites.update('A1', novos_dados)
        
        return True
    except Exception as e:
        st.error(f"❌ Erro ao salvar: {e}")
        return False

# Função para criar card de jogo
def criar_card_jogo(jogo, palpites, palpites_usuario, modo_visualizacao=False):
    with st.container():
        st.markdown('<div class="jogo-card">', unsafe_allow_html=True)
        
        id_jogo = int(jogo['ID_Jogo'])
        selecao_a = jogo['SeleçãoA']
        selecao_b = jogo['SeleçãoB']
        
        # Verificar palpite anterior
        palpite_anterior = palpites_usuario[palpites_usuario['id_jogo'] == str(id_jogo)]
        gols_a_default = int(palpite_anterior['PalpiteA'].iloc[0]) if not palpite_anterior.empty and palpite_anterior['PalpiteA'].iloc[0] != '' else 0
        gols_b_default = int(palpite_anterior['PalpiteB'].iloc[0]) if not palpite_anterior.empty and palpite_anterior['PalpiteB'].iloc[0] != '' else 0
        
        col1, col2, col3, col4, col5 = st.columns([3, 1, 1, 1, 3])
        
        with col1:
            st.markdown(f"### {selecao_a}")
        
        with col2:
            if modo_visualizacao:
                st.markdown(f"<h2 style='text-align: center; padding: 15px; background: #e0e0e0; border-radius: 10px;'>{gols_a_default}</h2>", unsafe_allow_html=True)
            else:
                gols_a = st.number_input("A", 0, 20, gols_a_default, key=f"golsA_{id_jogo}", label_visibility="collapsed")
        
        with col3:
            st.markdown("<h2 style='text-align: center; padding-top: 10px;'>X</h2>", unsafe_allow_html=True)
        
        with col4:
            if modo_visualizacao:
                st.markdown(f"<h2 style='text-align: center; padding: 15px; background: #e0e0e0; border-radius: 10px;'>{gols_b_default}</h2>", unsafe_allow_html=True)
            else:
                gols_b = st.number_input("B", 0, 20, gols_b_default, key=f"golsB_{id_jogo}", label_visibility="collapsed")
        
        with col5:
            st.markdown(f"### {selecao_b}")
        
        if not modo_visualizacao:
            palpites[id_jogo] = {'golsA': gols_a, 'golsB': gols_b}
        
        st.markdown('</div>', unsafe_allow_html=True)

# ==================== APP PRINCIPAL ====================

st.markdown('<p class="header-title">⚽ BOLÃO COPA DO MUNDO 2026 ⚽</p>', unsafe_allow_html=True)
st.markdown('<p style="text-align: center; color: #666; font-size: 1.2rem;">Faça seus palpites e boa sorte!</p>', unsafe_allow_html=True)
st.markdown("---")

# Carregar jogos
df_jogos = carregar_jogos()

if df_jogos is not None:
    # Sidebar
    with st.sidebar:
        st.title("🔐 Login")
        
        nome_participante = st.text_input("👤 Seu nome:", placeholder="Digite seu nome")
        codigo_participante = st.text_input("🔑 Seu código:", placeholder="Digite seu código", type="password")
        
        if st.button("✅ ENTRAR", use_container_width=True):
            if not nome_participante or not codigo_participante:
                st.error("⚠️ Preencha nome e código!")
            elif not validar_participante(nome_participante, codigo_participante):
                st.error("❌ Nome ou código inválido!")
            else:
                st.session_state['autenticado'] = True
                st.session_state['nome'] = nome_participante
                st.success(f"✅ Bem-vindo, {nome_participante}!")
                st.rerun()
        
        st.markdown("---")
        st.write("⏰ **Prazos por fase:**")
        for fase, _ in DATAS_LIMITE.items():
            tempo = tempo_restante(fase)
            if fase_dentro_do_prazo(fase):
                st.success(f"🟢 {fase}: {tempo}")
            else:
                st.error(f"🔒 {fase}: indisponível")
        
        st.markdown("---")
        st.info("💡 Não tem código? Contate o admin.")
    
    # Verificar autenticação
    if 'autenticado' not in st.session_state or not st.session_state['autenticado']:
        st.warning("👈 Faça login na barra lateral!")
    else:
        nome_logado = st.session_state['nome']
        
        df_palpites_exist = carregar_palpites_existentes()
        palpites_usuario = df_palpites_exist[df_palpites_exist['Participante'] == nome_logado]
        
        st.success(f"Olá, **{nome_logado}**! Preencha seus palpites nas fases disponíveis:")
        
        if not palpites_usuario.empty:
            st.info(f"ℹ️ Você já tem palpites salvos!")
        
        palpites = {}
        tem_fase_aberta = False
        
        fases_ordem = ['Grupo', '16 avos', 'Oitavas de final', 'Quartas de final', 'Semifinais', 'Terceiro e Quarto', 'Final']
        
        for fase in fases_ordem:
            jogos_fase = df_jogos[df_jogos['Fase'] == fase].copy()
            
            if len(jogos_fase) == 0:
                continue
            
            fase_aberta = fase_dentro_do_prazo(fase)
            if fase_aberta:
                tem_fase_aberta = True
            
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"## 🏆 {fase}")
            with col2:
                if fase_aberta:
                    st.success(f"⏰ {tempo_restante(fase)}")
                else:
                    st.error("🔒 indisponível")
            
            if not fase_aberta:
                st.markdown('<div class="fase-bloqueada">⚠️ Palpites desta fase indisponível</div>', unsafe_allow_html=True)
            
            if fase == 'Grupo':
                grupos = sorted(jogos_fase['Grupo'].unique())
                for grupo in grupos:
                    if pd.notna(grupo) and grupo != '':
                        st.markdown(f"### Grupo {grupo}")
                        jogos_grupo = jogos_fase[jogos_fase['Grupo'] == grupo]
                        for idx, jogo in jogos_grupo.iterrows():
                            criar_card_jogo(jogo, palpites, palpites_usuario, not fase_aberta)
            else:
                jogos_fase = jogos_fase.sort_values('ID_Jogo')
                for idx, jogo in jogos_fase.iterrows():
                    criar_card_jogo(jogo, palpites, palpites_usuario, not fase_aberta)
            
            st.markdown("---")
        
        if tem_fase_aberta:
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                if st.button("🚀 ENVIAR PALPITES", use_container_width=True):
                    if len(palpites) == 0:
                        st.error("⚠️ Preencha pelo menos um palpite!")
                    else:
                        with st.spinner('Salvando...'):
                            if salvar_palpites(nome_logado, palpites):
                                st.success(f"✅ {len(palpites)} palpites salvos!")
                                st.balloons()
                                # Limpar cache
                                st.cache_data.clear()
                            else:
                                st.error("❌ Erro ao salvar!")
        else:
            st.markdown('<div class="fase-bloqueada">🔒 Todas as fases encerradas</div>', unsafe_allow_html=True)

st.markdown("---")
st.markdown('<div style="text-align: center; color: #666;">Desenvolvido com ❤️ | Sistema na Nuvem 🌐</div>', unsafe_allow_html=True)
