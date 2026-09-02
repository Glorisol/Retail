import os
os.environ["GEMINI_API_KEY"] = os.getenv("GEMINI_API_KEY", "TU_API_KEY_AQUI")

import random
import pandas as pd
import altair as alt
import streamlit as st
from google import genai
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

st.set_page_config(page_title="Sabertec AI - Agente de Auditoría Retail", layout="wide")

@st.cache_data
def generar_datos_retail(num_registros=400):
    data = []
    sucursales = ["Tienda Centro", "Boulevard Norte", "Exprés Sur", "Mall Plaza"]
    
    start_date = pd.to_datetime("2026-08-01")
    for i in range(num_registros):
        sku = f"SKU-{5000 + i}"
        fecha = start_date + pd.Timedelta(hours=i)
        caducidad = fecha + pd.Timedelta(days=60)
        stock = random.randint(50, 500)
        merma = round(random.uniform(1.0, 99.0), 1)
        
        if merma > 75:
            estado = "CRITICO"
        elif merma > 50:
            estado = "REVISION"
        else:
            estado = "OPTIMO"
            
        data.append({
            "SKU": sku,
            "Fecha": str(fecha),
            "Fecha_Caducidad": str(caducidad)[:10],
            "Stock_Actual": stock,
            "Indice_Merma": merma,
            "Sucursal": random.choice(sucursales),
            "Estado_Auditoria": estado
        })
    return pd.DataFrame(data)

def consultar_agente_ia(prompt_usuario, total_skus, en_revision, criticos, merma_prom, umbral):
    try:
        client = genai.Client()
        prompt_sistema = f"""
        Actúa como un Agente Autónomo experto en auditoría retail de Sabertec AI.
        Instrucción del usuario: "{prompt_usuario}"
        Estadísticas actuales: Total SKUs: {total_skus}, En Revisión: {en_revision}, Críticos: {criticos}, Merma Promedio: {merma_prom}%.

        Genera un análisis gerencial altamente personalizado y específico para esta instrucción (máximo 3 párrafos cortos).
        """
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt_sistema
        )
        return response.text
    except Exception as e:
        return f"Análisis enfocado en la directriz: '{prompt_usuario}' sobre un total de {criticos} registros críticos detectados."

def construir_reporte_retail_por_estado(df_base, prompt_aplicado, texto_ia, ruta_salida="dictamen_merma_retail.pdf"):
    doc = SimpleDocTemplate(
        ruta_salida,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    
    styles = getSampleStyleSheet()
    estilo_titulo = ParagraphStyle('TituloGerencial', parent=styles['Heading1'], fontSize=12, leading=15, textColor=colors.HexColor("#1A365D"), spaceAfter=3)
    estilo_sub = ParagraphStyle('SubSeccion', parent=styles['Heading2'], fontSize=10, leading=13, textColor=colors.HexColor("#2C5282"), spaceBefore=6, spaceAfter=4)
    estilo_celda = ParagraphStyle('CeldaTexto', parent=styles['Normal'], fontSize=7.5, leading=9, textColor=colors.HexColor("#2D3748"))
    estilo_celda_header = ParagraphStyle('CeldaHeader', parent=styles['Normal'], fontSize=7.5, leading=9, textColor=colors.white, fontName="Helvetica-Bold")
    estilo_parrafo = ParagraphStyle('TextoParrafo', parent=styles['Normal'], fontSize=8.5, leading=12, textColor=colors.HexColor("#2D3748"), spaceBefore=4, spaceAfter=4)

    story = []
    
    # Encabezado principal del dictamen
    story.append(Paragraph("Sabertec Retail - Dictamen de Auditoría Autónoma (Capa 3 - Dictamen)", estilo_titulo))
    story.append(Paragraph("<b>DE:</b> Dirección de Auditoría y Control de Calidad & Agente Sabertec AI", estilo_celda))
    story.append(Paragraph("<b>PARA:</b> Dirección de Finanzas y Dirección de Operaciones", estilo_celda))
    story.append(Paragraph("<b>ASUNTO:</b> Informe Gerencial Consolidado de Seguimiento Operativo", estilo_celda))
    story.append(Paragraph("<b>FECHA:</b> 30 de Agosto, 2026", estilo_celda))
    story.append(Spacer(1, 4))
    
    story.append(Paragraph("Resumen Ejecutivo", estilo_sub))
    story.append(Paragraph(f"El agente autónomo procesó el universo completo de {len(df_base)} registros, segmentando de forma independiente los elementos bajo estatus de revisión y crítico para un control logístico riguroso.", estilo_parrafo))
    story.append(Paragraph(f"<b>Prompt Aplicado:</b> {prompt_aplicado}", estilo_parrafo))
    story.append(Spacer(1, 6))

    # Definición de colores y títulos para cada sección de estado
    config_estados = [
        ("REVISION", "1. Matriz Consolidada de Seguimiento Operativo (En Revisión)", colors.HexColor("#D69E2E")),
        ("CRITICO", "2. Matriz Consolidada de Seguimiento Operativo (Crítico)", colors.HexColor("#9B2C2C")),
        ("OPTIMO", "3. Matriz Consolidada de Seguimiento Operativo (Óptimo)", colors.HexColor("#22543D"))
    ]

    totales_por_estado = {}

    for idx, (estado_key, titulo_seccion, color_header) in enumerate(config_estados):
        df_estado = df_base[df_base["Estado_Auditoria"] == estado_key].copy()
        total_estado = len(df_estado)
        totales_por_estado[estado_key] = total_estado
        
        if idx > 0:
            story.append(PageBreak())
            
        story.append(Paragraph(f"{titulo_seccion} - Total: {total_estado} SKUs", estilo_sub))
        
        if total_estado == 0:
            story.append(Paragraph(f"No se registraron elementos bajo el estatus {estado_key}.", estilo_celda))
            continue
            
        df_clean = df_estado.drop(columns=["Estado_Auditoria"]).reset_index(drop=True)
        cols_a_mostrar = list(df_clean.columns)
        
        headers = [Paragraph(c, estilo_celda_header) for c in cols_a_mostrar]
        data_table = [headers]
        
        for _, row in df_clean.iterrows():
            data_table.append([Paragraph(str(row[c]), estilo_celda) for c in cols_a_mostrar])
            
        t = Table(data_table, colWidths=[85, 110, 95, 75, 75, 100], repeatRows=1)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), color_header),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 2),
            ('TOPPADDING', (0,0), (-1,-1), 2),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E0"))
        ]))
        story.append(t)

    # Bloque final con Hallazgos y Plan de Acción
    story.append(PageBreak())
    story.append(Paragraph("Hallazgos de Caducidad y Control Operativo:", estilo_sub))
    story.append(Paragraph("1. Control de Vencimientos: Se incorporan las fechas límite de caducidad para asegurar la aplicación del protocolo FEFO (First Expired, First Out) en tienda.", estilo_parrafo))
    story.append(Paragraph("2. Mitigación de Riesgos: Los lotes críticos requieren plan de contención urgente para evitar mermas financieras totales.", estilo_parrafo))
    story.append(Spacer(1, 4))
    
    story.append(Paragraph("Plan de Acción Dictaminado y Recomendaciones", estilo_sub))
    story.append(Paragraph("• <b>Acción Inmediata:</b> Despliegue de auditoría física en sucursales con SKUs críticos y revisión de rotación para los lotes en estado de revisión.", estilo_parrafo))
    story.append(Paragraph("• <b>Monitoreo Continuo:</b> Automatización diaria de ejecuciones mediante el agente Sabertec AI.", estilo_parrafo))
    
    texto_final = f"Dictamen Final: Evaluación completada de manera segregada. Se listan {totales_por_estado.get('REVISION', 0)} registros en revisión y {totales_por_estado.get('CRITICO', 0)} registros en estado crítico, incluyendo el control de caducidades."
    story.append(Paragraph(texto_final, estilo_parrafo))

    doc.build(story)
    return ruta_salida

st.markdown("### 🛍️ Sabertec AI: Agente de Auditoría & Analítica Retail")

with st.sidebar:
    st.markdown("### ⚙️ Configuración del Demo")
    st.info("ℹ️ **Modo Demostración Activo:** El prompt se encuentra preconfigurado para este escenario de control logístico.")

    # Prompt fijo de demostración (bloqueado para evitar alteraciones imprevistas)
    prompt_demo = "Monitorear riesgos de inventario, mermas críticas y desviaciones de precios en canales de retail, identificando productos de alta merma con alta rotación."
    
    st.text_area(
        "💬 Prompt Preconfigurado del Agente:",
        value=prompt_demo,
        height=130,
        disabled=True
    )
    
    registros_auditar = st.slider("Registros a Auditar", min_value=50, max_value=1000, value=400, step=50)
    umbral_alerta = st.slider("Umbral de Alerta de Desvío", min_value=10, max_value=100, value=70, step=5)
    
    ejecutar = st.button("🚀 Ejecutar Ciclo Autónomo del Agente", type="primary")

if ejecutar:
    st.session_state['ejecutado'] = True
    st.session_state['prompt_aplicado'] = prompt_demo
    st.session_state['registros'] = registros_auditar
    st.session_state['umbral'] = umbral_alerta

if not st.session_state.get('ejecutado', False):
    st.info("👉 Haz clic en **'Ejecutar Ciclo Autónomo del Agente'** en la barra lateral para iniciar la simulación del demo.")
else:
    st.error(f"**Prompt Aplicado (Demo):**\n\n\"{st.session_state['prompt_aplicado']}\"")
    
    df_data = generar_datos_retail(st.session_state['registros'])

    total_skus = len(df_data)
    en_revision = len(df_data[df_data["Estado_Auditoria"] == "REVISION"])
    criticos = len(df_data[df_data["Estado_Auditoria"] == "CRITICO"])
    merma_prom = round(df_data["Indice_Merma"].mean(), 1)

    with st.spinner("🤖 El Agente está analizando los datos según el prompt de demostración..."):
        analisis_ia = consultar_agente_ia(st.session_state['prompt_aplicado'], total_skus, en_revision, criticos, merma_prom, st.session_state['umbral'])

    st.markdown("### 📑 1. Dictamen del Agente Inteligente")
    st.success(analisis_ia)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("SKUs Totales Base", total_skus)
    m2.metric("SKUs En Revisión", en_revision)
    m3.metric("SKUs Críticos", criticos)
    m4.metric("Registros Base", len(df_data))

    st.markdown("### 📊 2. Distribución General del Inventario")
    conteo_df = df_data["Estado_Auditoria"].value_counts().reset_index()
    conteo_df.columns = ['Estado', 'Cantidad']
    
    chart = alt.Chart(conteo_df).mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
        x=alt.X('Estado:N', sort=['OPTIMO', 'REVISION', 'CRITICO'], title='Estado de Auditoría'),
        y=alt.Y('Cantidad:Q', title='Cantidad de SKUs'),
        color=alt.Color('Estado:N', scale=alt.Scale(
            domain=['OPTIMO', 'REVISION', 'CRITICO'],
            range=['#22543D', '#D69E2E', '#9B2C2C']
        ), legend=None)
    ).properties(height=280)
    st.altair_chart(chart, use_container_width=True)

    st.markdown("### 🚨 3. Hallazgos Críticos: Alerta de Mermas y Desviaciones")
    col_h1, col_h2 = st.columns(2)
    with col_h1:
        st.warning(f"**Punto crítico detectado:** Se identificaron SKUs con índices de merma superiores al umbral tolerable ({st.session_state['umbral']}) en el universo analizado.")
    with col_h2:
        st.error("**Acción Preventiva:** Bloqueo temporal de reabastecimiento automático en las sucursales con desviación severa hasta completar la auditoría física.")

    st.markdown("### 📋 4. Escrutinio Completo y Detalle de SKUs")
    st.markdown(f"Explora la matriz completa de los **{total_skus}** productos auditados y filtra por estatus operativo:")

    filtro_estatus = st.selectbox("🔍 Filtrar SKUs por Estatus Operativo:", ["TODOS", "OPTIMO", "REVISION", "CRITICO"])

    if filtro_estatus != "TODOS":
        df_filtrado_tabla = df_data[df_data["Estado_Auditoria"] == filtro_estatus].copy()
        df_mostrar_tabla = df_filtrado_tabla.drop(columns=["Estado_Auditoria"])
    else:
        df_filtrado_tabla = df_data.copy()
        df_mostrar_tabla = df_data.copy()

    st.dataframe(df_mostrar_tabla.reset_index(drop=True), use_container_width=True)

    st.markdown("### ⚙️ 5. Plan de Acción y Recomendaciones Correctivas")
    st.markdown("""
    - **Protocolos de Recepción:** Reforzar la validación estricta de bultos y conteo ciego en centros de distribución y tiendas de alta rotación.
    - **Monitoreo Automático:** Programar ejecuciones diarias del agente autónomo para control preventivo de inventario.
    - **Ajustes de Precios:** Sincronizar de forma centralizada las listas de precios para evitar desfasajes entre pasarela POS y tienda online.
    """)

    pdf_path = construir_reporte_retail_por_estado(df_data, st.session_state['prompt_aplicado'], analisis_ia)
    
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        st.download_button("📥 Descargar CSV Filtrado", df_filtrado_tabla.to_csv(index=False).encode('utf-8'), "matriz_filtrada.csv", "text/csv")
    with col_d2:
        with open(pdf_path, "rb") as f:
            st.download_button("📥 Descargar Dictamen en PDF", f, "dictamen_merma_retail.pdf", "application/pdf", type="primary")