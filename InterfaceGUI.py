"""
InterfaceGUI.py - Interface gráfica do simulador (TR1 - UnB)

Feita com a biblioteca Streamlit (a tela abre no navegador). Este arquivo só
desenha a tela: quem simula as camadas é o Simulador.py.

A tela tem três partes:
    1. Barra lateral: a "Configuração geral" da Figura 1 do enunciado
    2. Chat de texto entre a Estação A e a Estação B
    3. Detalhes: a saída de cada camada, lado a lado para transmissor e receptor
"""

import html
import math

import streamlit as st
from matplotlib.figure import Figure

import CamadaEnlace
import CamadaFisica


# Em toda a tela, azul representa o transmissor e verde representa o receptor
COR_DO_TRANSMISSOR = '#4F46E5'
COR_DO_RECEPTOR = '#0F766E'

FOLHA_DE_ESTILO = """
<style>
    [data-testid="stMainBlockContainer"] { max-width: 1280px; padding-top: 3rem; }

    /* ---------- chat ---------- */
    .estacao { display: flex; align-items: center; gap: 0.65rem; }
    .estacao-letra {
        width: 2.3rem; height: 2.3rem; border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        background: #1E293B; color: #FFFFFF; font-weight: 700;
    }
    .estacao-nome { font-weight: 600; line-height: 1.2; }
    .estacao-legenda { font-size: 0.78rem; color: #64748B; }

    /* column-reverse deixa a conversa sempre rolada até a última mensagem */
    .conversa {
        height: 300px; overflow-y: auto; padding: 0 0.3rem;
        display: flex; flex-direction: column-reverse;
    }
    .conversa-vazia {
        height: 300px; display: flex; align-items: center; justify-content: center;
        text-align: center; color: #94A3B8; font-size: 0.9rem;
    }
    .linha { display: flex; flex-direction: column; margin: 0.45rem 0; }
    .linha.enviada { align-items: flex-end; }
    .linha.recebida { align-items: flex-start; }
    .bolha {
        max-width: 85%; padding: 0.5rem 0.85rem; border-radius: 1rem;
        font-size: 0.95rem; line-height: 1.35;
        white-space: pre-wrap; overflow-wrap: anywhere;
    }
    .enviada .bolha { background: #4F46E5; color: #FFFFFF; border-bottom-right-radius: 0.25rem; }
    .recebida .bolha { background: #E6F4F1; color: #0F172A; border-bottom-left-radius: 0.25rem; }
    .rodape { font-size: 0.72rem; color: #64748B; margin-top: 0.15rem; }
    .situacao { font-weight: 600; }
    .situacao.ok { color: #15803D; }
    .situacao.corrigido { color: #B45309; }
    .situacao.erro { color: #DC2626; }

    /* ---------- detalhes da transmissão ---------- */
    .etiqueta {
        display: inline-block; margin: 0 0.35rem 0.35rem 0; padding: 0.15rem 0.6rem;
        border-radius: 999px; border: 1px solid #E2E8F0;
        background: #F8FAFC; color: #334155; font-size: 0.78rem;
    }
    .lado { padding: 0.4rem 0.8rem; border-radius: 0.5rem; font-weight: 700; }
    .lado.tx { background: #EEF2FF; color: #3730A3; }
    .lado.rx { background: #E6F4F1; color: #115E59; }
    .camada {
        font-size: 0.75rem; font-weight: 700; color: #64748B;
        text-transform: uppercase; letter-spacing: 0.08em;
    }
    .etapa { display: flex; align-items: center; flex-wrap: wrap; gap: 0.45rem; margin-bottom: 0.35rem; }
    .etapa-numero {
        width: 1.45rem; height: 1.45rem; border-radius: 50%;
        display: inline-flex; align-items: center; justify-content: center;
        color: #FFFFFF; font-size: 0.72rem; font-weight: 700;
    }
    .etapa-numero.tx { background: #4F46E5; }
    .etapa-numero.rx { background: #0F766E; }
    .etapa-numero.meio { background: #64748B; }
    .etapa-titulo { font-weight: 600; font-size: 0.92rem; }
    .etapa-detalhe { font-size: 0.78rem; color: #64748B; }
    .caixa {
        background: #F8FAFC; color: #1E293B; border: 1px solid #E2E8F0;
        border-radius: 0.5rem; padding: 0.5rem 0.7rem;
        max-height: 7.8rem; overflow-y: auto; overflow-wrap: anywhere;
    }
    .caixa.bits { font-family: "Source Code Pro", monospace; font-size: 0.78rem; line-height: 1.55; }
    .caixa.texto { white-space: pre-wrap; }
    .caixa.vazia { color: #94A3B8; font-style: italic; }
    .contagem { font-size: 0.72rem; color: #64748B; margin-top: 0.2rem; }
    .bit-errado { background: #DC2626; color: #FFFFFF; font-weight: 700; border-radius: 2px; }
    .bit-edc { background: #FEF3C7; color: #92400E; font-weight: 700; }
    .medidas { display: flex; flex-wrap: wrap; gap: 0.6rem 2.5rem; margin-top: 0.4rem; }
    .medida-rotulo { font-size: 0.78rem; color: #64748B; }
    .medida-valor { font-size: 1.3rem; font-weight: 600; }
</style>
"""


# =============================================================================
# Funções pequenas de apoio
# =============================================================================

def executando_no_streamlit():
    """Diz se o programa foi iniciado com "streamlit run" (e não com "python")."""
    return st.runtime.exists()


def obter_historico():
    """Devolve a lista de mensagens do chat, que o Streamlit guarda entre as atualizações da tela."""
    if 'historico' not in st.session_state:
        st.session_state['historico'] = []
    return st.session_state['historico']


def _texto_seguro(texto):
    """Prepara um texto para entrar no HTML da página.

    Caracteres de controle (que o ruído pode criar) viram '�', e os símbolos
    especiais do HTML, como '<', são escapados.
    """
    visivel = ''
    for caractere in texto:
        codigo = ord(caractere)
        eh_de_controle = codigo < 32 or 127 <= codigo < 160
        if eh_de_controle and caractere != '\n':
            visivel += '�'
        else:
            visivel += caractere
    return html.escape(visivel)


def _resumir(texto, limite):
    """Corta um texto longo para ele caber em uma linha de menu."""
    texto = texto.replace('\n', ' ')
    if len(texto) > limite:
        return texto[:limite] + '…'
    return texto


def _contar_bits_diferentes(bits_a, bits_b):
    """Conta em quantas posições as duas sequências de bits são diferentes."""
    diferentes = 0
    for posicao in range(min(len(bits_a), len(bits_b))):
        if bits_a[posicao] != bits_b[posicao]:
            diferentes += 1
    return diferentes


def _relacao_sinal_ruido(sinal_transmitido, sinal_recebido):
    """Relação sinal-ruído em decibéis: 10 * log10(potência do sinal / potência do ruído)."""
    potencia_do_sinal = 0.0
    potencia_do_ruido = 0.0
    for n in range(len(sinal_transmitido)):
        ruido = sinal_recebido[n] - sinal_transmitido[n]
        potencia_do_sinal += sinal_transmitido[n] ** 2
        potencia_do_ruido += ruido ** 2

    if potencia_do_ruido == 0:
        return 'sem ruído'
    if potencia_do_sinal == 0:
        return 'sem sinal'
    decibeis = 10 * math.log10(potencia_do_sinal / potencia_do_ruido)
    return f'{decibeis:.1f} dB'


def _usa_portadora(config):
    """True quando a mensagem foi enviada com modulação por portadora."""
    return config['modulacao_por_portadora'] != CamadaFisica.SEM_PORTADORA


def _nome_do_edc(config):
    """Nome do método de detecção/correção, com o tamanho quando for checksum."""
    if config['edc'] == 'Checksum':
        tamanho = config['tamanho_do_checksum']
        return f'Checksum de {tamanho} bits'
    return config['edc']


# =============================================================================
# 1. Barra lateral: configuração geral
# =============================================================================

def _escolher_tamanho_do_edc(edc):
    """Campo "Tamanho do EDC" da Figura 1. Só o checksum permite escolher o tamanho."""
    if edc == 'Checksum':
        return st.selectbox(
            'Tamanho do EDC (bits)', CamadaEnlace.TAMANHOS_DE_CHECKSUM, index=1,
            help='Tamanho das palavras somadas e do checksum anexado ao quadro.')

    if edc == 'Bit de paridade par':
        tamanho_fixo = '1 bit'
    elif edc == 'CRC-32':
        tamanho_fixo = '32 bits'
    else:
        tamanho_fixo = '3 bits a cada 4 bits de dados'
    st.selectbox('Tamanho do EDC', [tamanho_fixo], disabled=True,
                 help='Neste método o tamanho é fixo.')

    # valor que só é usado quando o método escolhido é o checksum
    return 16


def desenhar_configuracao():
    """Desenha a barra lateral e devolve um dicionário com todas as escolhas."""
    with st.sidebar:
        st.header('Configuração geral')

        st.subheader('Camada de enlace')
        tamanho_maximo_do_quadro = st.number_input(
            'Tamanho máximo de quadro (caracteres)', min_value=1, max_value=255, value=16,
            help='Mensagens maiores que isso são divididas em vários quadros.')
        enquadramento = st.selectbox(
            'Tipo de enquadramento', CamadaEnlace.TIPOS_DE_ENQUADRAMENTO,
            help='Como o receptor descobre onde o quadro começa e termina.')
        edc = st.selectbox(
            'Tipo de detecção ou correção', CamadaEnlace.TIPOS_DE_EDC, index=2,
            help='Paridade, checksum e CRC-32 só detectam erros. O Hamming corrige 1 bit por bloco.')
        tamanho_do_checksum = _escolher_tamanho_do_edc(edc)

        st.subheader('Camada física')
        # O Streamlit guarda o valor de cada campo em st.session_state antes de
        # redesenhar a tela. Por isso dá para saber a portadora escolhida antes
        # de desenhar o campo dela, que fica mais abaixo.
        portadora_atual = st.session_state.get('modulacao_por_portadora', CamadaFisica.SEM_PORTADORA)
        usa_portadora = portadora_atual != CamadaFisica.SEM_PORTADORA
        if usa_portadora:
            # Figura 1: o modulador recebe sempre o sinal NRZ do codificador banda base
            st.session_state['modulacao_digital'] = 'NRZ-Polar'

        modulacao_digital = st.radio(
            'Tipo de modulação digital (banda base)', CamadaFisica.MODULACOES_DIGITAIS,
            key='modulacao_digital', disabled=usa_portadora,
            help='Com portadora, o modulador recebe sempre o sinal NRZ-Polar (Figura 1 do enunciado).')
        modulacao_por_portadora = st.selectbox(
            'Tipo de modulação analógica (portadora)', CamadaFisica.MODULACOES_POR_PORTADORA,
            key='modulacao_por_portadora',
            help='Em "Nenhuma", o sinal banda base vai direto para o meio de comunicação.')
        amplitude = st.slider('Amplitude do sinal (V)', 0.5, 5.0, 1.0, 0.5)
        frequencia = st.slider(
            'Frequência da portadora (ciclos por bit)', 1, 4, 2, disabled=not usa_portadora)

        st.subheader('Meio de comunicação')
        st.caption('Ruído gaussiano n(x, σ) somado à tensão de cada amostra do sinal.')
        media_do_ruido = st.slider('Média x (V)', -2.0, 2.0, 0.0, 0.1)
        desvio_do_ruido = st.slider('Desvio padrão σ (V)', 0.0, 5.0, 0.0, 0.1)

    return {
        'tamanho_maximo_do_quadro': tamanho_maximo_do_quadro,
        'enquadramento': enquadramento,
        'edc': edc,
        'tamanho_do_checksum': tamanho_do_checksum,
        'modulacao_digital': modulacao_digital,
        'modulacao_por_portadora': modulacao_por_portadora,
        'amplitude': amplitude,
        'frequencia': frequencia,
        'media_do_ruido': media_do_ruido,
        'desvio_do_ruido': desvio_do_ruido,
    }


# =============================================================================
# 2. Chat
# =============================================================================

def preparar_pagina():
    """Configura a página, aplica o visual e escreve o título."""
    st.set_page_config(page_title='Simulador TR1', page_icon='📡', layout='wide')
    st.html(FOLHA_DE_ESTILO)
    st.title('Simulador das camadas física e de enlace')
    st.caption('Teleinformática e Redes 1 · Cada mensagem do chat desce pelas camadas do '
               'transmissor, atravessa o meio com ruído e sobe pelas camadas do receptor.')


def _desenhar_estacao(coluna, estacao, outra_estacao):
    """Desenha o quadro de uma estação: cabeçalho, espaço da conversa e campo de digitação.

    Devolve o espaço da conversa (preenchido depois) e o texto que acabou de
    ser digitado (None quando nada foi enviado).
    """
    with coluna:
        with st.container(border=True):
            st.html(f'''
                <div class="estacao">
                    <div class="estacao-letra">{estacao}</div>
                    <div>
                        <div class="estacao-nome">Estação {estacao}</div>
                        <div class="estacao-legenda">conversando com a Estação {outra_estacao}</div>
                    </div>
                </div>''')
            area_da_conversa = st.container()
            texto_digitado = st.chat_input(
                f'Mensagem para a Estação {outra_estacao}',
                key='entrada_da_estacao_' + estacao, max_chars=500)
    return area_da_conversa, texto_digitado


def desenhar_chat(historico):
    """Desenha as duas estações lado a lado.

    Devolve os espaços das conversas e a lista das mensagens recém-digitadas,
    no formato (remetente, texto).
    """
    coluna_do_titulo, coluna_do_botao = st.columns([5, 1], vertical_alignment='bottom')
    coluna_do_titulo.subheader('Chat')
    if coluna_do_botao.button('Limpar', help='Apaga todas as mensagens da conversa.'):
        historico.clear()

    coluna_a, coluna_b = st.columns(2)
    area_a, texto_a = _desenhar_estacao(coluna_a, 'A', 'B')
    area_b, texto_b = _desenhar_estacao(coluna_b, 'B', 'A')

    mensagens_digitadas = []
    if texto_a:
        mensagens_digitadas.append(('A', texto_a))
    if texto_b:
        mensagens_digitadas.append(('B', texto_b))

    areas_das_conversas = {'A': area_a, 'B': area_b}
    return areas_das_conversas, mensagens_digitadas


def _situacao_da_mensagem(mensagem):
    """Resume o que o receptor concluiu sobre a mensagem. Devolve (tipo, texto)."""
    quantidade_de_quadros = len(mensagem['quadros_rx'])
    quadros_com_erro = 0
    bits_corrigidos = 0
    for quadro in mensagem['quadros_rx']:
        if quadro['erro_detectado'] or quadro['aviso_do_enquadramento'] != '':
            quadros_com_erro += 1
        bits_corrigidos += quadro['bits_corrigidos']

    if quadros_com_erro > 0:
        return 'erro', f'Erro detectado em {quadros_com_erro} de {quantidade_de_quadros} quadro(s)'
    if bits_corrigidos > 0:
        return 'corrigido', f'Hamming corrigiu {bits_corrigidos} bit(s)'
    return 'ok', 'Recebida sem erros'


def _bolha_enviada(numero, mensagem):
    """HTML do balão de uma mensagem que a estação enviou."""
    texto = _texto_seguro(mensagem['texto_enviado'])
    horario = mensagem['horario']
    return f'''
        <div class="linha enviada">
            <div class="bolha">{texto}</div>
            <div class="rodape">#{numero} · {horario}</div>
        </div>'''


def _bolha_recebida(numero, mensagem):
    """HTML do balão de uma mensagem que a estação recebeu, com o resultado da verificação."""
    texto = _texto_seguro(mensagem['texto_recebido'])
    if texto == '':
        texto = '<i>(nenhum texto pôde ser recuperado)</i>'
    horario = mensagem['horario']
    tipo, situacao = _situacao_da_mensagem(mensagem)
    return f'''
        <div class="linha recebida">
            <div class="bolha">{texto}</div>
            <div class="rodape">#{numero} · {horario} · <span class="situacao {tipo}">{situacao}</span></div>
        </div>'''


def mostrar_conversas(areas_das_conversas, historico):
    """Preenche a conversa de cada estação com as mensagens enviadas e recebidas por ela."""
    for estacao in ['A', 'B']:
        bolhas = ''
        for posicao in range(len(historico)):
            mensagem = historico[posicao]
            numero = posicao + 1
            if mensagem['remetente'] == estacao:
                bolhas += _bolha_enviada(numero, mensagem)
            else:
                bolhas += _bolha_recebida(numero, mensagem)

        with areas_das_conversas[estacao]:
            if bolhas == '':
                st.html('<div class="conversa-vazia">Nenhuma mensagem ainda.<br>'
                        'Escreva no campo abaixo para começar.</div>')
            else:
                st.html(f'<div class="conversa"><div>{bolhas}</div></div>')


# =============================================================================
# 3. Detalhes da transmissão
# =============================================================================

def _titulo_da_etapa(numero, titulo, detalhe, lado):
    """HTML do título de uma etapa: número colorido, nome e um detalhe em cinza."""
    return f'''
        <div class="etapa">
            <span class="etapa-numero {lado}">{numero}</span>
            <span class="etapa-titulo">{titulo}</span>
            <span class="etapa-detalhe">{detalhe}</span>
        </div>'''


def _caixa_de_texto(texto):
    """HTML de uma caixa mostrando um texto."""
    if texto == '':
        return '<div class="caixa vazia">(vazio)</div>'
    return f'<div class="caixa texto">{_texto_seguro(texto)}</div>'


def _caixa_de_bits(bits, bits_de_referencia='', inicio_do_edc=None):
    """HTML de uma caixa mostrando bits, agrupados de 8 em 8.

    bits_de_referencia: os bits que eram esperados. Os diferentes ficam em vermelho.
    inicio_do_edc: posição a partir da qual os bits são o código de erro (em amarelo).
    """
    if bits == '':
        return '<div class="caixa vazia">(vazio)</div>'

    partes = []
    for posicao in range(len(bits)):
        bit = bits[posicao]
        if posicao > 0 and posicao % 8 == 0:
            partes.append(' ')

        chegou_errado = posicao < len(bits_de_referencia) and bit != bits_de_referencia[posicao]
        faz_parte_do_edc = inicio_do_edc is not None and posicao >= inicio_do_edc
        if chegou_errado:
            partes.append(f'<span class="bit-errado">{bit}</span>')
        elif faz_parte_do_edc:
            partes.append(f'<span class="bit-edc">{bit}</span>')
        else:
            partes.append(bit)

    bits_formatados = ''.join(partes)
    quantidade = len(bits)
    return (f'<div class="caixa bits">{bits_formatados}</div>'
            f'<div class="contagem">{quantidade} bits</div>')


def _medida(rotulo, valor):
    """HTML de um número em destaque com o nome dele em cima."""
    return f'''
        <div>
            <div class="medida-rotulo">{rotulo}</div>
            <div class="medida-valor">{valor}</div>
        </div>'''


def _mostrar_grafico(sinal, cor, bits_no_grafico):
    """Desenha o começo de um sinal: tensão (V) em função do tempo (em períodos de bit)."""
    quantidade_de_amostras = min(len(sinal), bits_no_grafico * CamadaFisica.AMOSTRAS_POR_BIT)
    tempos = []
    tensoes = []
    for n in range(quantidade_de_amostras):
        tempos.append(n / CamadaFisica.AMOSTRAS_POR_BIT)
        tensoes.append(sinal[n])

    figura = Figure(figsize=(6.4, 2.0))
    eixo = figura.subplots()
    eixo.plot(tempos, tensoes, color=cor, linewidth=1.2)
    eixo.axhline(0, color='#94A3B8', linewidth=0.6)

    # uma marca no eixo do tempo a cada bit (ou a cada grupo, se forem muitos bits)
    passo = max(1, bits_no_grafico // 16)
    eixo.set_xticks(list(range(0, bits_no_grafico + 1, passo)))
    eixo.set_xlim(0, quantidade_de_amostras / CamadaFisica.AMOSTRAS_POR_BIT)
    eixo.set_xlabel('tempo (períodos de bit)', fontsize=8)
    eixo.set_ylabel('tensão (V)', fontsize=8)
    eixo.tick_params(labelsize=7)
    eixo.grid(True, color='#E2E8F0', linewidth=0.6)
    eixo.spines['top'].set_visible(False)
    eixo.spines['right'].set_visible(False)
    st.pyplot(figura)


def _escolher_o_que_mostrar(historico):
    """Menus para escolher a mensagem, o quadro e o trecho dos gráficos."""
    coluna_da_mensagem, coluna_do_quadro, coluna_do_grafico = st.columns([3, 2, 2])

    rotulos_das_mensagens = []
    for posicao in range(len(historico)):
        mensagem = historico[posicao]
        numero = posicao + 1
        remetente = mensagem['remetente']
        destinatario = mensagem['destinatario']
        resumo = _resumir(mensagem['texto_enviado'], 30)
        rotulos_das_mensagens.append(f'#{numero} · {remetente} → {destinatario} · {resumo}')

    # a lista de opções muda a cada mensagem nova, e o menu volta para a mais recente
    rotulo_escolhido = coluna_da_mensagem.selectbox(
        'Mensagem', rotulos_das_mensagens, index=len(rotulos_das_mensagens) - 1)
    posicao_da_mensagem = rotulos_das_mensagens.index(rotulo_escolhido)
    mensagem = historico[posicao_da_mensagem]

    quantidade_de_quadros = len(mensagem['quadros_tx'])
    rotulos_dos_quadros = []
    for posicao in range(quantidade_de_quadros):
        numero = posicao + 1
        resumo = _resumir(mensagem['quadros_tx'][posicao]['texto'], 16)
        rotulos_dos_quadros.append(f'{numero} de {quantidade_de_quadros} · {resumo}')

    rotulo_escolhido = coluna_do_quadro.selectbox(
        'Quadro', rotulos_dos_quadros, key=f'quadro_da_mensagem_{posicao_da_mensagem}',
        disabled=quantidade_de_quadros == 1)
    numero_do_quadro = rotulos_dos_quadros.index(rotulo_escolhido)

    bits_no_grafico = coluna_do_grafico.slider('Bits mostrados nos gráficos', 8, 64, 16, 8)
    return mensagem, numero_do_quadro, bits_no_grafico


def _mostrar_situacao_do_quadro(tx, rx, config):
    """Faixa colorida dizendo o que aconteceu com o quadro escolhido."""
    nome_do_edc = _nome_do_edc(config)
    houve_erro = False
    if rx['erro_detectado']:
        st.error(f'Erro detectado ({nome_do_edc}): o receptor sinaliza este quadro como corrompido.')
        houve_erro = True
    if rx['aviso_do_enquadramento'] != '':
        aviso = rx['aviso_do_enquadramento']
        st.error(f'Quadro com estrutura corrompida: {aviso}.')
        houve_erro = True
    if houve_erro:
        return

    if rx['texto'] != tx['texto']:
        # só o simulador sabe disso: o receptor aceitou o quadro achando que estava certo
        st.warning(f'O texto chegou diferente do enviado e o receptor não percebeu: havia mais '
                   f'erros do que o método {nome_do_edc} consegue tratar.')
    elif rx['bits_corrigidos'] > 0:
        corrigidos = rx['bits_corrigidos']
        st.success(f'O Hamming corrigiu {corrigidos} bit(s) e o quadro foi recuperado.')
    else:
        st.success('Quadro recebido sem erros.')


def _mostrar_aplicacao(tx, rx):
    """Camada de aplicação: texto e bits, no transmissor e no receptor."""
    with st.container(border=True):
        st.html('<div class="camada">Camada de aplicação</div>')

        coluna_tx, coluna_rx = st.columns(2)
        coluna_tx.html(_titulo_da_etapa(1, 'Entrada de texto', '', 'tx')
                       + _caixa_de_texto(tx['texto']))
        coluna_rx.html(_titulo_da_etapa(13, 'Saída de texto', '', 'rx')
                       + _caixa_de_texto(rx['texto']))

        coluna_tx, coluna_rx = st.columns(2)
        coluna_tx.html(_titulo_da_etapa(2, 'Codificador em bits', '8 bits por caractere', 'tx')
                       + _caixa_de_bits(tx['bits_da_aplicacao']))
        coluna_rx.html(_titulo_da_etapa(12, 'Desenquadramento', 'bits entregues à aplicação', 'rx')
                       + _caixa_de_bits(rx['bits_da_aplicacao'], tx['bits_da_aplicacao']))


def _mostrar_enlace(tx, rx, config):
    """Camada de enlace: quadro e quadro com código de erro, no transmissor e no receptor."""
    nome_do_edc = _nome_do_edc(config)

    # nos métodos de detecção o código é anexado depois do quadro, e dá para destacá-lo;
    # no Hamming as paridades ficam espalhadas entre os dados
    if config['edc'] == 'Hamming':
        inicio_do_edc = None
    else:
        inicio_do_edc = len(tx['quadro'])

    with st.container(border=True):
        st.html('<div class="camada">Camada de enlace</div>')

        coluna_tx, coluna_rx = st.columns(2)
        coluna_tx.html(_titulo_da_etapa(3, 'Enquadramento', config['enquadramento'], 'tx')
                       + _caixa_de_bits(tx['quadro']))
        coluna_rx.html(_titulo_da_etapa(11, 'Detecção e correção de erros', 'quadro sem o código', 'rx')
                       + _caixa_de_bits(rx['quadro'], tx['quadro']))

        coluna_tx, coluna_rx = st.columns(2)
        coluna_tx.html(_titulo_da_etapa(4, 'Detecção e correção de erros', nome_do_edc, 'tx')
                       + _caixa_de_bits(tx['quadro_com_edc'], '', inicio_do_edc))
        coluna_rx.html(_titulo_da_etapa(10, 'Bits recebidos', 'saída da camada física', 'rx')
                       + _caixa_de_bits(rx['bits_recebidos'], tx['quadro_com_edc']))

        st.caption('Amarelo: código de erro anexado ao quadro. '
                   'Vermelho: bits que chegaram diferentes dos transmitidos.')


def _mostrar_fisica(tx, rx, config, bits_no_grafico):
    """Camada física: os quatro "amostradores de sinal" da Figura 1."""
    usa_portadora = _usa_portadora(config)
    if usa_portadora:
        nome_do_codificador = 'NRZ-Polar'
    else:
        nome_do_codificador = config['modulacao_digital']

    with st.container(border=True):
        st.html('<div class="camada">Camada física</div>')

        # linha da banda base
        coluna_tx, coluna_rx = st.columns(2)
        with coluna_tx:
            st.html(_titulo_da_etapa(5, 'Codificador banda base', nome_do_codificador, 'tx'))
            _mostrar_grafico(tx['sinal_banda_base'], COR_DO_TRANSMISSOR, bits_no_grafico)
        with coluna_rx:
            if usa_portadora:
                detalhe = 'NRZ entregue pelo demodulador'
            else:
                detalhe = 'sinal que chegou do meio'
            st.html(_titulo_da_etapa(9, 'Decodificador banda base', detalhe, 'rx'))
            _mostrar_grafico(rx['sinal_banda_base'], COR_DO_RECEPTOR, bits_no_grafico)

        # linha da portadora
        coluna_tx, coluna_rx = st.columns(2)
        with coluna_tx:
            if usa_portadora:
                st.html(_titulo_da_etapa(6, 'Modulador', config['modulacao_por_portadora'], 'tx'))
                _mostrar_grafico(tx['sinal_modulado'], COR_DO_TRANSMISSOR, bits_no_grafico)
            else:
                st.html(_titulo_da_etapa(6, 'Modulador', 'não usado: transmissão em banda base', 'tx'))
        with coluna_rx:
            if usa_portadora:
                st.html(_titulo_da_etapa(8, 'Demodulador', 'sinal que chegou do meio', 'rx'))
                _mostrar_grafico(rx['sinal_recebido'], COR_DO_RECEPTOR, bits_no_grafico)
            else:
                st.html(_titulo_da_etapa(8, 'Demodulador', 'não usado: transmissão em banda base', 'rx'))


def _mostrar_meio(tx, rx, config):
    """Meio de comunicação: o ruído aplicado e o estrago que ele causou no quadro."""
    media = config['media_do_ruido']
    desvio = config['desvio_do_ruido']
    bits_trocados = _contar_bits_diferentes(tx['quadro_com_edc'], rx['bits_recebidos'])
    bits_enviados = len(tx['quadro_com_edc'])

    with st.container(border=True):
        relacao_sinal_ruido = _relacao_sinal_ruido(tx['sinal_transmitido'], rx['sinal_recebido'])
        st.html('<div class="camada">Meio de comunicação</div>'
                + _titulo_da_etapa(7, 'Ruído gaussiano somado ao sinal',
                                   'entre o transmissor e o receptor', 'meio')
                + '<div class="medidas">'
                + _medida('Média do ruído (x)', f'{media:.1f} V')
                + _medida('Desvio padrão do ruído (σ)', f'{desvio:.1f} V')
                + _medida('Relação sinal-ruído', relacao_sinal_ruido)
                + _medida('Bits trocados pelo ruído', f'{bits_trocados} de {bits_enviados}')
                + '</div>')


def mostrar_detalhes(historico):
    """Mostra, para uma mensagem do chat, a saída de cada etapa da Figura 1."""
    st.subheader('Por dentro da transmissão')
    if len(historico) == 0:
        st.info('Envie uma mensagem no chat para ver aqui a saída de cada camada, '
                'no transmissor e no receptor.')
        return

    mensagem, numero_do_quadro, bits_no_grafico = _escolher_o_que_mostrar(historico)
    config = mensagem['config']
    tx = mensagem['quadros_tx'][numero_do_quadro]
    rx = mensagem['quadros_rx'][numero_do_quadro]

    # resumo da configuração usada nesta mensagem
    if _usa_portadora(config):
        nome_da_camada_fisica = 'NRZ-Polar → ' + config['modulacao_por_portadora']
    else:
        nome_da_camada_fisica = config['modulacao_digital'] + ' (banda base)'
    amplitude = config['amplitude']
    etiquetas = [config['enquadramento'], _nome_do_edc(config), nome_da_camada_fisica,
                 f'amplitude de {amplitude:.1f} V']
    html_das_etiquetas = ''
    for etiqueta in etiquetas:
        html_das_etiquetas += f'<span class="etiqueta">{etiqueta}</span>'
    st.html(html_das_etiquetas)

    _mostrar_situacao_do_quadro(tx, rx, config)

    remetente = mensagem['remetente']
    destinatario = mensagem['destinatario']
    coluna_tx, coluna_rx = st.columns(2)
    coluna_tx.html(f'<div class="lado tx">Transmissor (TX) · Estação {remetente}</div>')
    coluna_rx.html(f'<div class="lado rx">Receptor (RX) · Estação {destinatario}</div>')

    _mostrar_aplicacao(tx, rx)
    _mostrar_enlace(tx, rx, config)
    _mostrar_fisica(tx, rx, config, bits_no_grafico)
    _mostrar_meio(tx, rx, config)
