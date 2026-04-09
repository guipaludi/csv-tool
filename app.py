import json
import os
import tempfile
import zipfile
from io import BytesIO

import pandas as pd
import streamlit as st


st.title("CSV Tool")

modo_entrada = st.radio("Tipo de entrada", ("ZIP", "Folder"), horizontal=True)

if modo_entrada == "ZIP":
    uploaded_input = st.file_uploader("Upload do ZIP", type="zip")
else:
    uploaded_input = st.file_uploader(
        "Upload da pasta",
        type=["json", "zip"],
        accept_multiple_files="directory",
    )

termo_busca = st.text_input(
    "Termo para buscar dentro dos JSONs",
    value="",
)

campos_input = st.text_input(
    "Campos para retorno (separados por virgula)",
    value="dialogId,message_type,time",
)

gerar = st.button("Generate CSV")

if gerar:
    if not campos_input.strip() and not termo_busca.strip():
        st.warning("Preencha ao menos os campos ou o termo de busca.")
        st.stop()

    if not uploaded_input:
        if modo_entrada == "ZIP":
            st.warning("Faca upload de um ZIP.")
        else:
            st.warning("Faca upload de uma pasta.")
        st.stop()


def ler_json_flexivel_bytes(raw_bytes):
    for encoding in ("utf-8", "latin-1"):
        try:
            return json.loads(raw_bytes.decode(encoding))
        except Exception:
            pass

    for encoding in ("utf-8", "latin-1"):
        try:
            texto = raw_bytes.decode(encoding)
            linhas = texto.splitlines()

            objetos = []
            for linha in linhas:
                linha = linha.strip()
                if not linha:
                    continue

                try:
                    objetos.append(json.loads(linha))
                except Exception:
                    pass

            return objetos if objetos else None
        except Exception:
            pass

    return None


def extrair_valor(obj, campo):
    if isinstance(obj, dict):
        if campo in obj:
            return obj[campo]
        for valor in obj.values():
            resultado = extrair_valor(valor, campo)
            if resultado is not None:
                return resultado

    elif isinstance(obj, list):
        for item in obj:
            resultado = extrair_valor(item, campo)
            if resultado is not None:
                return resultado

    return None


def encontrar_termo(obj, termo):
    termo = termo.lower().strip()

    if isinstance(obj, dict):
        for valor in obj.values():
            resultado = encontrar_termo(valor, termo)
            if resultado:
                return resultado

    elif isinstance(obj, list):
        for item in obj:
            resultado = encontrar_termo(item, termo)
            if resultado:
                return resultado

    else:
        texto = str(obj)
        if termo in texto.lower():
            return texto

    return None


def processar_objetos_json(content, campos, termo_busca, dados, caminho_atual):
    objetos = content if isinstance(content, list) else [content]

    for obj in objetos:
        match = None

        if termo_busca:
            match = encontrar_termo(obj, termo_busca)
            if not match:
                continue

        linha = {}

        if termo_busca:
            linha["match"] = match

        for campo in campos:
            valor = extrair_valor(obj, campo)

            if campo == "message_type" and not valor and "message_type=" in caminho_atual:
                valor = caminho_atual.split("message_type=")[1].split("/")[0]

            linha[campo] = valor

        dados.append(linha)


def contar_jsons_no_zip(zip_file):
    total = 0

    for info in zip_file.infolist():
        if info.is_dir():
            continue

        nome_interno = info.filename

        try:
            conteudo = zip_file.read(info)
        except Exception:
            continue

        if nome_interno.lower().endswith(".zip"):
            try:
                with zipfile.ZipFile(BytesIO(conteudo), "r") as nested_zip:
                    total += contar_jsons_no_zip(nested_zip)
            except Exception:
                continue
            continue

        if nome_interno.lower().endswith(".json"):
            total += 1

    return total


def atualizar_progresso(progresso, status_texto, progresso_estado, caminho_atual):
    progresso_estado["processados"] += 1
    total = progresso_estado["total"] or 1
    fracao = progresso_estado["processados"] / total
    progresso.progress(min(fracao, 1.0))
    status_texto.text(
        f"Processando JSON {progresso_estado['processados']}/{progresso_estado['total']}: {caminho_atual}"
    )


def contar_jsons_em_arquivos(uploaded_files):
    total = 0

    for uploaded_file in uploaded_files:
        nome_arquivo = uploaded_file.name.replace("\\", "/")
        conteudo = uploaded_file.getvalue()

        if nome_arquivo.lower().endswith(".zip"):
            try:
                with zipfile.ZipFile(BytesIO(conteudo), "r") as nested_zip:
                    total += contar_jsons_no_zip(nested_zip)
            except Exception:
                continue
            continue

        if nome_arquivo.lower().endswith(".json"):
            total += 1

    return total


def processar_zip_recursivo(
    zip_file,
    campos,
    termo_busca,
    dados,
    progresso,
    status_texto,
    progresso_estado,
    caminho_zip="",
):
    for info in zip_file.infolist():
        if info.is_dir():
            continue

        nome_interno = info.filename
        caminho_atual = f"{caminho_zip}/{nome_interno}" if caminho_zip else nome_interno

        try:
            conteudo = zip_file.read(info)
        except Exception:
            st.warning(f"Erro ao ler arquivo compactado: {caminho_atual}")
            continue

        if nome_interno.lower().endswith(".zip"):
            try:
                with zipfile.ZipFile(BytesIO(conteudo), "r") as nested_zip:
                    processar_zip_recursivo(
                        nested_zip,
                        campos,
                        termo_busca,
                        dados,
                        progresso,
                        status_texto,
                        progresso_estado,
                        caminho_atual,
                    )
            except Exception:
                st.warning(f"Erro ao abrir ZIP interno: {caminho_atual}")
            continue

        if not nome_interno.lower().endswith(".json"):
            continue

        try:
            content = ler_json_flexivel_bytes(conteudo)
            if not content:
                atualizar_progresso(progresso, status_texto, progresso_estado, caminho_atual)
                continue

            processar_objetos_json(content, campos, termo_busca, dados, caminho_atual)
            atualizar_progresso(progresso, status_texto, progresso_estado, caminho_atual)
        except Exception:
            st.warning(f"Erro no arquivo: {caminho_atual}")
            atualizar_progresso(progresso, status_texto, progresso_estado, caminho_atual)


def processar_arquivos_upload(
    uploaded_files,
    campos,
    termo_busca,
    dados,
    progresso,
    status_texto,
    progresso_estado,
):
    for uploaded_file in uploaded_files:
        nome_arquivo = uploaded_file.name.replace("\\", "/")
        conteudo = uploaded_file.getvalue()

        if nome_arquivo.lower().endswith(".zip"):
            try:
                with zipfile.ZipFile(BytesIO(conteudo), "r") as nested_zip:
                    processar_zip_recursivo(
                        nested_zip,
                        campos,
                        termo_busca,
                        dados,
                        progresso,
                        status_texto,
                        progresso_estado,
                        nome_arquivo,
                    )
            except Exception:
                st.warning(f"Erro ao abrir ZIP interno: {nome_arquivo}")
            continue

        if not nome_arquivo.lower().endswith(".json"):
            continue

        try:
            content = ler_json_flexivel_bytes(conteudo)
            if not content:
                atualizar_progresso(progresso, status_texto, progresso_estado, nome_arquivo)
                continue

            processar_objetos_json(content, campos, termo_busca, dados, nome_arquivo)
            atualizar_progresso(progresso, status_texto, progresso_estado, nome_arquivo)
        except Exception:
            st.warning(f"Erro no arquivo: {nome_arquivo}")
            atualizar_progresso(progresso, status_texto, progresso_estado, nome_arquivo)


if gerar and uploaded_input:
    campos = [campo.strip() for campo in campos_input.split(",") if campo.strip()]
    dados = []
    progresso = st.progress(0.0)
    status_texto = st.empty()

    if modo_entrada == "ZIP":
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = os.path.join(tmpdir, "arquivo.zip")
            with open(zip_path, "wb") as arquivo_zip:
                arquivo_zip.write(uploaded_input.read())

            try:
                with zipfile.ZipFile(zip_path, "r") as zip_ref:
                    total_jsons = contar_jsons_no_zip(zip_ref)
                    progresso_estado = {"processados": 0, "total": total_jsons}

                    if total_jsons == 0:
                        progresso.progress(1.0)
                        status_texto.text("Nenhum JSON encontrado no ZIP.")
                    else:
                        status_texto.text(f"Encontrados {total_jsons} JSONs. Iniciando processamento...")
                        processar_zip_recursivo(
                            zip_ref,
                            campos,
                            termo_busca,
                            dados,
                            progresso,
                            status_texto,
                            progresso_estado,
                        )
                        progresso.progress(1.0)
                        status_texto.text(
                            f"Processamento concluido: {total_jsons}/{total_jsons} JSONs lidos."
                        )
            except Exception:
                st.error("Erro ao abrir ZIP.")
                st.stop()
    else:
        total_jsons = contar_jsons_em_arquivos(uploaded_input)
        progresso_estado = {"processados": 0, "total": total_jsons}

        if total_jsons == 0:
            progresso.progress(1.0)
            status_texto.text("Nenhum JSON encontrado na pasta.")
        else:
            status_texto.text(f"Encontrados {total_jsons} JSONs. Iniciando processamento...")
            processar_arquivos_upload(
                uploaded_input,
                campos,
                termo_busca,
                dados,
                progresso,
                status_texto,
                progresso_estado,
            )
            progresso.progress(1.0)
            status_texto.text(f"Processamento concluido: {total_jsons}/{total_jsons} JSONs lidos.")

    if dados:
        df = pd.DataFrame(dados)
        st.success(f"{len(df)} registros encontrados")
        st.dataframe(df, use_container_width=True)

        csv = df.to_csv(index=False, sep=";").encode("utf-8-sig")

        st.download_button(
            "Baixar CSV",
            csv,
            "resultado.csv",
            "text/csv",
        )
    else:
        st.warning("Nenhum resultado encontrado.")
