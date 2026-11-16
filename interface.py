import streamlit as st
import socket
import matplotlib.pyplot as plt

from link_layer import Link
from deteccao_erros import DeteccaoErros
from physical_layer import PhysicalLayer

st.set_page_config(layout="wide")
st.title("Simulador de Comunicação - Camadas Física e de Enlace")

with st.sidebar:
    st.subheader("Configurações")
    mensagem = st.text_input("Digite a mensagem:", "Olá, mundo!")

    modulacao = st.radio("Modulação", ['nrz', 'manchester', 'bipolar', 'ask', 'fsk', 'psk', 'qam'])
    enquadramento = st.radio("Enquadramento", ['count', 'bits', 'bytes', 'entrelacamento'])
    tamanho_quadro = st.slider("Tamanho máximo do quadro (caracteres)", 1, 255, 16)
    deteccao = st.radio("Detecção de Erros", ['crc', 'paridade', 'hamming', 'checksum'])

    st.markdown("**Parâmetros do sinal**")
    amplitude = st.slider("Amplitude (V)", 0.5, 5.0, 1.0, 0.5)
    frequencia = st.slider("Frequência", 1, 15, 5)

    st.markdown("**Ruído gaussiano n(x, σ)**")
    media_ruido = st.slider("Média x (V)", -2.0, 2.0, 0.0, 0.1)
    desvio_ruido = st.slider("Desvio padrão σ (V)", 0.0, 3.0, 0.0, 0.1)

    enviar = st.button("Enviar")


# Divide a mensagem em pedaços de no máximo 'tamanho' caracteres (cada pedaço = 1 quadro)
def dividir_em_quadros(texto, tamanho):
    return [texto[i:i + tamanho] for i in range(0, len(texto), tamanho)] or ['']


# Camada de enlace: enquadra um pedaço de texto conforme o tipo escolhido
def enquadrar(link, phy, texto):
    bits = phy.texto_para_bits(texto)
    if enquadramento == 'count':
        return link.enquadrar_count(bits)
    if enquadramento == 'bits':
        return link.enquadrar_bitstuffing(bits)
    if enquadramento == 'entrelacamento':
        return link.enquadrar_entrelacamento(bits)
    # bytes: o stuffing é feito sobre os caracteres e depois convertido para bits
    return phy.texto_para_bits(link.enquadrar_bytestuffing(texto))


# Camada física: transforma os bits em sinal elétrico (V) conforme a modulação escolhida
def modular(phy, bits):
    if modulacao == 'nrz':
        return phy.nrz_polar(bits, A=amplitude)
    if modulacao == 'manchester':
        return phy.manchester(bits, A=amplitude)
    if modulacao == 'bipolar':
        return phy.bipolar(bits, A=amplitude)
    if modulacao == 'ask':
        return phy.ask(bits, A=amplitude, f=frequencia)
    if modulacao == 'fsk':
        return phy.fsk(bits, f0=frequencia, f1=frequencia*2, A=amplitude)
    if modulacao == 'psk':
        return phy.psk(bits, A=amplitude, f=frequencia)
    return phy.qam32(bits, A=amplitude, f=frequencia)


# Desenha um sinal no tempo (degraus para banda base, curva para portadora)
def plotar(phy, sinal, titulo):
    fig = plt.figure(figsize=(10, 3))
    if modulacao in ['nrz', 'manchester', 'bipolar']:
        plt.step(range(len(sinal)*2), [v for x in sinal for v in (x, x)], where='post')
        plt.xlim(0, 50)
    else:
        plt.plot(phy.tempo, sinal)
        plt.xlim(0, 20)
    plt.title(f"{titulo} ({modulacao.upper()})")
    plt.xlabel("Tempo")
    plt.ylabel("Tensão (V)")
    plt.grid(True)
    st.pyplot(fig)
    plt.close(fig)


# Envia um quadro ao receptor e devolve (texto recebido, bits recebidos, status dos erros)
def enviar_ao_servidor(bits_codificados, sinal_recebido):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect(('localhost', 5000))
        s.sendall(modulacao.encode() + b'\n')
        s.sendall(deteccao.encode() + b'\n')
        s.sendall(enquadramento.encode() + b'\n')
        s.sendall((str(amplitude) + '\n').encode())
        s.sendall((str(frequencia) + '\n').encode())
        # quantidade de bits reais (a modulação pode completar com zeros extras)
        s.sendall((str(len(bits_codificados)) + '\n').encode())
        s.sendall((','.join(map(str, sinal_recebido)) + '\n').encode())

        resposta = s.makefile('r', encoding='utf-8')
        texto = resposta.readline().rstrip('\n')
        bits_rx = resposta.readline().strip()
        status = resposta.readline().strip()
    return texto, bits_rx, status


# Mostra o resultado da verificação de erros em uma caixa colorida
def mostrar_status(status):
    if status == 'OK':
        st.success("Nenhum erro detectado")
    elif 'Erro' in status:
        st.error(status)
    else:
        st.warning(status)  # ex.: Hamming corrigiu bits


# Marca em vermelho os bits recebidos que chegaram diferentes dos enviados
def marcar_bits(bits_rx, bits_enviados):
    return ''.join(
        f"<span style='color:#e24b4a;font-weight:700'>{b}</span>"
        if i < len(bits_enviados) and b != bits_enviados[i] else b
        for i, b in enumerate(bits_rx)
    )


# Botão "Enviar": cada quadro passa por enlace -> física -> meio (ruído) -> receptor
if enviar:
    if any(ord(c) > 255 for c in mensagem):
        st.error("A mensagem tem caracteres fora da tabela de 8 bits (ex.: emoji, €). Remova-os.")
        st.stop()

    st.subheader("Resultados da Transmissão")
    link, phy, det = Link(), PhysicalLayer(), DeteccaoErros(deteccao)
    pedacos = dividir_em_quadros(mensagem, tamanho_quadro)
    resumo = st.container()  # preenchido no fim, mas aparece no topo

    textos_recebidos, problemas = [], []
    for n, pedaco in enumerate(pedacos, 1):
        quadro = enquadrar(link, phy, pedaco)
        bits_codificados = det.adicionar(quadro)
        sinal = modular(phy, bits_codificados)
        sinal_recebido = phy.adicionar_ruido(sinal, media_ruido, desvio_ruido)  # meio de comunicação

        if n == 1:  # gráficos do primeiro quadro
            plotar(phy, sinal, "Sinal transmitido - quadro 1")
            plotar(phy, sinal_recebido, "Sinal recebido com ruído - quadro 1")

        texto_rx, bits_rx, status = enviar_ao_servidor(bits_codificados, sinal_recebido)
        textos_recebidos.append(texto_rx)
        if status != 'OK':
            problemas.append(f"Quadro {n}: {status}")

        with st.expander(f"Quadro {n} de {len(pedacos)}: '{pedaco}'", expanded=(len(pedacos) == 1)):
            st.markdown(f"**Bits gerados:** `{phy.texto_para_bits(pedaco)}`")
            st.markdown(f"**Bits enquadrados:** `{quadro}`")
            st.markdown(f"**Bits com código de erro:** `{bits_codificados}`")
            st.markdown(f"**Bits recebidos:** <code>{marcar_bits(bits_rx, bits_codificados)}</code>",
                        unsafe_allow_html=True)
            mostrar_status(status)

    with resumo:
        st.markdown(f"**Mensagem dividida em {len(pedacos)} quadro(s)** de até {tamanho_quadro} caracteres")
        st.markdown(f"**Mensagem recebida no servidor:** `{''.join(textos_recebidos)}`")
        mostrar_status('; '.join(problemas) if problemas else 'OK')
