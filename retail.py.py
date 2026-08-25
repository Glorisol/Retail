import streamlit as st
import pandas as pd
import altair as alt
import google.genai as genai
import io
import re

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

st.set_page_config(page_title="Sabertec | Agente Inteligente de Retail", layout="wide")

GEMINI_API_KEY = "AQ.Ab8RN6JsAK9Sr2sqdsbF67Yn3wez6FlbAnMa_pWnrLsCn-qzoQ"

st.markdown("""
    <style>
    .stApp { background-color: #F8FAFC; }
    h1 { color: #0F172A; }
    .cta-box { background-color: #0F172A; color: #FFFFFF; padding: 20px; border-radius: 10px; text-align: center; margin-top: 30px; }
    .welcome-box { background-color: #EFF6FF; border-left: 5px solid #3B82F6; padding: 15px; border-radius: 5px; margin-top: 20px; margin-bottom: 20px; }
    </style>
""", unsafe_allow_html=True)

st.title("⚡ Sabertec | Agente IA de Auditoría Operativa y Retail")
st.markdown("Demo de análisis automatizado de inventarios, mermas y quiebres de stock con datos precargados del sector consumo masivo.")

datos_ventas = {
    'id_ventas': [f'V-{100+i}' for i in range(1, 51)],
    'tienda': ['Caracas Centro', 'Maracaibo Norte', 'Valencia Sur', 'Barquisimeto Este', 'Maracay Plaza'] * 10,
    'producto_id': ['PROD-01', 'PROD-02', 'PROD-03', 'PROD-04', 'PROD-05', 'PROD-06', 'PROD-07', 'PROD-08', 'PROD-09', 'PROD-10'] * 5,
    'nombre_producto': ['Leche Completa 1L', 'Arroz Premium 1kg', 'Harina de Maíz 1kg', 'Aceite Vegetal 1L', 'Detergente Líquido', 'Shampoo Control Caspa', 'Queso Blanco Duro 1kg', 'Café Molido 500g', 'Atún en Enlatado', 'Pasta Regulada 1kg'] * 5,
    'categoría': ['Alimentos', 'Alimentos', 'Alimentos', 'Alimentos', 'Limpieza', 'Cuidado Personal', 'Charcutería', 'Alimentos', 'Alimentos', 'Alimentos'] * 5,
    'cantidad': [12, -1, 45, 0, 15, 8, -2, 30, 50, 14] * 5,
    'precio_unitario': [2.5, 1.2, 1.1, 3.5, 5.8, 4.2, 6.5, 4.0, 1.8, 0.9] * 5,
    'monto_total': [30.0, -1.2, 49.5, 0.0, 87.0, 33.6, -13.0, 120.0, 90.0, 12.6] * 5
}
df_ventas_local = pd.DataFrame(datos_ventas)
datos_inventario = {
    'producto_id': [f'PROD-{i:02d}' for i in range(1, 11)] * 5,
    'nombre_producto': ['Leche Completa 1L', 'Arroz Premium 1kg', 'Harina de Maíz 1kg', 'Aceite Vegetal 1L', 'Detergente Líquido', 'Shampoo Control Caspa', 'Queso Blanco Duro 1kg', 'Café Molido 500g', 'Atún en Enlatado', 'Pasta Regulada 1kg'] * 5,
    'tienda': ['Caracas Centro'] * 10 + ['Maracaibo Norte'] * 10 + ['Valencia Sur'] * 10 + ['Barquisimeto Este'] * 10 + ['Maracay Plaza'] * 10,
    'stock_teorico_sistema': [150, 200, 350, 90, 120, 80, 110, 95, 300, 140] * 5,
    'stock_fisico_conteo': [105, 205, 265, 90, 95, 82, 97, 95, 295, 140] * 5,
    'diferencia_unidades': [
        -45, 5, -85, 0, -25, 2, -30, 0, -12, 0,  
        -12, 0, -20, 1, -5, 0, -8, 3, -2, 0,     
        -28, 2, -50, 0, -18, 0, -19, 0, -7, 1,    
        -5, 1, -10, 0, -2, 0, -4, 0, -1, 0,      
        -18, 0, -35, 2, -10, 4, -15, 1, -5, 0     
    ],
    'estado_auditoria': ['Faltante Crítico', 'Sobrante Corregido', 'Faltante Crítico', 'Alineado', 'Faltante Moderado', 'Alineado', 'Faltante Crítico', 'Alineado', 'Faltante Moderado', 'Alineado'] * 5
}
df_inventario_local = pd.DataFrame(datos_inventario)

datos_riesgo = {
    'producto_id': [f'PROD-{i:02d}' for i in range(1, 11)] * 5,
    'nombre_producto': ['Leche Completa 1L', 'Arroz Premium 1kg', 'Harina de Maíz 1kg', 'Aceite Vegetal 1L', 'Detergente Líquido', 'Shampoo Control Caspa', 'Queso Blanco Duro 1kg', 'Café Molido 500g', 'Atún en Enlatado', 'Pasta Regulada 1kg'] * 5,
    'proveedor_principal': ['Lácteos del Centro', 'Arrocería Nacional', 'Molinos del País', 'Oleaginosas Occidente', 'Químicos Globales', 'Cosméticos Bell', 'Distribuidora Los Andes', 'Cafetalera Andina', 'Enlatados del Mar', 'Molinos del País'] * 5,
    'dias_para_vencer': [4, 180, 240, 120, 360, 500, -2, 90, 450, 15] * 5,
    'nivel_rotacion': ['Alta', 'Media', 'Alta', 'Media', 'Baja', 'Baja', 'Alta', 'Alta', 'Media', 'Alta'] * 5,
    'alerta_riesgo': ['Vencimiento Cercano', 'Sin Riesgo', 'Sin Riesgo', 'Sin Riesgo', 'Sobre-stock / Baja Rotación', 'Sin Riesgo', 'Producto Vencido en Anaquel', 'Sin Riesgo', 'Sin Riesgo', 'Revisión Requerida'] * 5
}
df_riesgo_local = pd.DataFrame(datos_riesgo)

dfs_fijos = {
    'Movimientos_Ventas': df_ventas_local,
    'Inventario_Teorico_vs_Fisico': df_inventario_local,
    'Riesgo_Caducidad_y_Rotacion': df_riesgo_local
}

def create_clean_pdf(texto_informe, dfs_dict):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    elements = []
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=15, textColor=colors.HexColor('#0F172A'), alignment=1, spaceAfter=12)
    heading_style = ParagraphStyle('HeadingStyle', parent=styles['Heading2'], fontSize=11, textColor=colors.HexColor('#0F172A'), spaceBefore=12, spaceAfter=4, fontName='Helvetica-Bold')
    body_style = ParagraphStyle('BodyStyle', parent=styles['Normal'], fontSize=9, textColor=colors.HexColor('#334155'), spaceAfter=5, leading=12)
    cell_style = ParagraphStyle('CellStyle', parent=styles['Normal'], fontSize=7, textColor=colors.HexColor('#1E293B'), leading=9)
    elements.append(Paragraph("SABERTEC - Dictamen de Auditoría de Retail e Inventarios", title_style))
    elements.append(Spacer(1, 5))
    texto_limpio_ia = re.sub(r'#+\s?', '', texto_informe)
    elements.append(Paragraph("Informe Ejecutivo del Agente", heading_style))
    for paragraph in texto_limpio_ia.split('\n'):
        p_text = paragraph.strip()
        if p_text and not p_text.startswith('---'):
            es_subtitulo = (p_text.isupper() and len(p_text) > 4 or p_text.endswith(':') or any(keyword in p_text.upper() for keyword in ["RESUMEN EJECUTIVO", "HALLAZGOS", "DICTAMEN", "RECOMENDACIONES", "CRÍTICO"]))
            if es_subtitulo:
                elements.append(Paragraph(p_text, heading_style))
            else:
                elements.append(Paragraph(p_text, body_style))
    elements.append(Spacer(1, 10))
    ancho_pagina_util = 540 
    for nombre, df in dfs_dict.items():
        elements.append(Paragraph(f"Muestra de Datos: {nombre}", heading_style))
        df_sample = df.head(8).fillna("")
        table_data = []
        header_row = [Paragraph(f"<b>{str(col)}</b>", cell_style) for col in df_sample.columns]
        table_data.append(header_row)
        for _, row in df_sample.iterrows():
            row_data = [Paragraph(str(val), cell_style) for val in row.values]
            table_data.append(row_data)
        num_cols = len(df_sample.columns)
        col_width = ancho_pagina_util / max(num_cols, 1)
        col_widths = [col_width] * num_cols
        t = Table(table_data, colWidths=col_widths)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0F172A')),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('BOTTOMPADDING', (0,0), (-1,0), 4),
            ('TOPPADDING', (0,0), (-1,0), 4),
            ('BACKGROUND', (0,1), (-1,-1), colors.HexColor('#F8FAFC')),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 10))
    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()
st.markdown("### 📊 Tableros de Control de Mermas e Inventarios (Datos de la Cadena)")
col_g1, col_g2 = st.columns(2)
with col_g1:
    st.markdown("#### 📉 Pérdidas/Mermas de Inventario por Tienda")
    df_agrupado = df_inventario_local.groupby('tienda')['diferencia_unidades'].sum().reset_index()
    chart = alt.Chart(df_agrupado).mark_bar().encode(
        x=alt.X('tienda:N', title='Tiendas Auditadas', sort='y'),
        y=alt.Y('diferencia_unidades:Q', title='Diferencia Total Unidades (Faltantes)'),
        color=alt.Color('tienda:N', title='Tienda', scale=alt.Scale(scheme='tableau10'))
    ).properties(height=300)
    st.altair_chart(chart, use_container_width=True)
with col_g2:
    st.markdown("#### ⚠️ Distribución de Alertas Críticas de Caducidad")
    df_counts = df_riesgo_local['alerta_riesgo'].value_counts().reset_index()
    df_counts.columns = ['Alerta', 'Cantidad']
    chart_risk = alt.Chart(df_counts).mark_arc(innerRadius=50).encode(
        theta=alt.Theta(field="Cantidad", type="quantitative"),
        color=alt.Color(field="Alerta", type="nominal", scale=alt.Scale(scheme='category10')),
        tooltip=['Alerta', 'Cantidad']
    ).properties(height=300)
    st.altair_chart(chart_risk, use_container_width=True)

# SECCIÓN ESTRATÉGICA DE BIENVENIDA Y EXPLICACIÓN DE DATOS PREVIOS AL PROMPT
st.markdown(f"""
    <div class="welcome-box">
        <h4>👋 ¡Hola! Analicé los datos operativos de tus tiendas en tiempo real:</h4>
        <p>A simple vista se identifican anomalías severas en el inventario de <b>Caracas Centro</b> y un volumen crítico de alertas por <b>productos vencidos o merma por caducidad</b> en anaquel. El sistema ya consolidó las muestras sustanciosas de 50 registros de Ventas, Inventario Físico y Riesgo de Proveedores.</p>
        <p>💡 <b>Instrucción para la Demo:</b> Puedes personalizar el enfoque del Agente modificando el cuadro de texto de abajo (por ejemplo, pidiendo priorizar pérdidas económicas o evaluar cajeros específicos) para generar un dictamen de auditoría corporativa automatizado e inmediato.</p>
    </div>
""", unsafe_allow_html=True)

user_prompt = st.text_area("Modifica el enfoque del prompt del Agente si lo deseas:", value="Realiza una auditoría integral cruzando las ventas, las diferencias de inventario físico y las alertas de riesgo por caducidad en las tiendas.", height=80)

if st.button("🧠 Activar Razonamiento del Agente de Retail", type="primary"):
    with st.spinner("🤖 El agente está cruzando los 3 archivos internos y auditando..."):
        contexto_documentos = ""
        for nombre, df in dfs_fijos.items():
            contexto_documentos += f"\n\n=== ARCHIVO LOCAL: {nombre} (Muestra Completa de 50 registros estructurados) ===\n" + df.to_string()
        try:
            client = genai.Client(api_key=GEMINI_API_KEY)
            instruccion_maestra_permanente = """
            ERES UN AGENTE AUDITOR SENIOR EXPERTO EN RETAIL Y CONSUMO MASIVO DE SABERTEC.
            Tus reglas de oro son:
            1. Analiza con criterio de negocio los tres conjuntos de datos adjuntos: Movimientos_Ventas (busca mermas por montos negativos o precios de $0), Inventario_Teorico_vs_Fisico (analiza los faltantes críticos por robo u omisión), y Riesgo_Caducidad_y_Rotacion (identifica productos vencidos en góndola o sobrestock estancado).
            2. REGLA ESTRICTA: Redacta el informe única y exclusivamente en lenguaje gerencial corporativo de alto nivel, ideal para directores de operaciones y finanzas. NO incluyas código de programación, marcas de código markdown de programación, ni menciones a Python en el texto del dictamen.
            3. Estructura el dictamen con: Resumen Ejecutivo de Operaciones, Hallazgos Críticos detectados por Tienda, Pérdidas Económicas Estimadas, y un Plan de Recomendaciones Inmediatas para mitigar la merma.
            """
            prompt_final = f"{instruccion_maestra_permanente}\nINSTRUCCIÓN ESPECÍFICA: {user_prompt}\nDatos del Sistema de Retail:\n{contexto_documentos}"
            response = client.models.generate_content(model='gemini-3.6-flash', contents=prompt_final)
            texto_limpio = response.text.replace("**", "")
            st.session_state['analisis_hecho'] = True
            st.session_state['informe_texto'] = texto_limpio
            st.session_state['pdf_data'] = create_clean_pdf(texto_limpio, dfs_fijos)
        except Exception as err:
            st.error(f"⚠️ Error de conexión con Google Gemini: {str(err)}")

if st.session_state.get('analisis_hecho', False):
    st.success("✅ Auditoría de Retail completada con éxito.")
    st.markdown("### 📋 Dictamen de Auditoría Operativa")
    st.markdown(st.session_state['informe_texto'])
    st.markdown("---")
    st.markdown("### 📥 Exportar Reportes para Gerencia")
    col_exp1, col_exp2 = st.columns(2)
    with col_exp1:
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            for nombre, df in dfs_fijos.items():
                df.to_excel(writer, sheet_name=nombre[:31], index=False)
        st.download_button("📊 Descargar Tablas Consolidadas (Excel)", data=output.getvalue(), file_name="Auditoria_Retail_Sabertec.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    with col_exp2:
        st.download_button("📄 Descargar Dictamen Gerencial Oficial (PDF)", data=st.session_state['pdf_data'], file_name="Dictamen_Auditoria_Retail.pdf", mime="application/pdf")
    st.markdown("""
        <div class="cta-box">
            <h3>🚀 ¿Quieres implementar este Agente de Retail en los procesos de tu empresa?</h3>
            <p>Optimiza la rentabilidad en anaquel, frena el hurto interno y automatiza la conciliación de mermas con la tecnología de Sabertec.</p>
        </div>
    """, unsafe_allow_html=True)
    col_cta1, col_cta2 = st.columns(2)
    with col_cta1:
        email_lead = st.text_input("Ingresa tu correo corporativo:", placeholder="operaciones@empresa.com", key="input_lead")
    with col_cta2:
        st.write("")
        st.write("")
        if st.button("📩 Solicitar Demo Presencial Sabertec", type="primary"):
            if email_lead and "@" in email_lead:
                st.success(f"¡Excelente! Hemos registrado tu solicitud para el correo **{email_lead}**. Te contactaremos para coordinar la demo de retail.")
            else:
                st.warning("Por favor ingresa un correo electrónico válido.")
