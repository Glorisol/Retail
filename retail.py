import streamlit as st
import pandas as pd
import altair as alt
import google.genai as genai
from google.genai import types
import io
import time
import re

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

st.set_page_config(page_title="Sabertec | Agente Autónomo de Retail", layout="wide")

GEMINI_API_KEY = "AQ.Ab8RN6JsAK9Sr2sqdsbF67Yn3wez6FlbAnMa_pWnrLsCn-qzoQ"

st.markdown("""
    <style>
    .stApp { background-color: #F8FAFC; }
    h1 { color: #0F172A; }
    .cta-box { background-color: #0F172A; color: #FFFFFF; padding: 20px; border-radius: 10px; text-align: center; margin-top: 30px; }
    .welcome-box { background-color: #EFF6FF; border-left: 5px solid #3B82F6; padding: 15px; border-radius: 5px; margin-top: 20px; margin-bottom: 20px; }
    </style>
""", unsafe_allow_html=True)

st.title("⚡ Sabertec | Agente Autónomo IA de Auditoría Operativa y Retail")
st.markdown("Demo corporativa basada en arquitectura de Agentes Autónomos con *Function Calling* y auditoría dinámica de inventarios.")

# --- DATOS PRECARGADOS ---
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

# --- HERRAMIENTAS (TOOLS) PARA EL AGENTE AUTÓNOMO ---
def consultar_inventario_por_tienda(tienda: str) -> str:
    """Permite al agente consultar de forma autónoma el inventario físico y teórico de una tienda específica.
    Args:
        tienda: Nombre exacto de la tienda (ej: 'Caracas Centro', 'Maracaibo Norte', 'Valencia Sur', 'Barquisimeto Este', 'Maracay Plaza')
    """
    df_filtrado = df_inventario_local[df_inventario_local['tienda'].str.contains(tienda, case=False, na=False)]
    if df_filtrado.empty:
        return f"No se encontraron registros para la tienda {tienda}."
    return df_filtrado.to_string(index=False)

def consultar_alertas_caducidad() -> str:
    """Permite al agente consultar de forma autónoma los productos vencidos o con riesgo crítico de caducidad en anaquel."""
    df_filtrado = df_riesgo_local[df_riesgo_local['dias_para_vencer'] <= 15]
    return df_filtrado.to_string(index=False)

def auditar_ventas_anomalas() -> str:
    """Permite al agente consultar transacciones de ventas con montos negativos o mermas atípicas registradas."""
    df_filtrado = df_ventas_local[df_ventas_local['monto_total'] < 0]
    if df_filtrado.empty:
        return "No se detectaron ventas con montos negativos."
    return df_filtrado.to_string(index=False)

available_tools = [
    consultar_inventario_por_tienda,
    consultar_alertas_caducidad,
    auditar_ventas_anomalas
]

# --- GENERACIÓN DE PDF PROFESIONAL OPTIMIZADO (ESTILOS UNIFORMES Y 100% NEGRITA) ---
def create_clean_pdf(texto_informe, dfs_dict):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    elements = []
    styles = getSampleStyleSheet()
    
    body_style = ParagraphStyle(
        'UniformBody',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#0F172A'),
        spaceAfter=6
    )
    
    header_meta_style = ParagraphStyle(
        'UniformMeta',
        parent=body_style,
        spaceAfter=4
    )
    
    heading_style = ParagraphStyle(
        'UniformHeading',
        parent=body_style,
        spaceBefore=10,
        spaceAfter=4
    )
    
    cell_style = ParagraphStyle(
        'UniformCell',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=colors.HexColor('#0F172A')
    )
    
    header_cell_style = ParagraphStyle(
        'UniformHeaderCell',
        parent=cell_style,
        textColor=colors.white
    )

    elements.append(Paragraph("SABERTEC - AUDITORÍA OPERATIVA Y RETAIL", heading_style))
    elements.append(Spacer(1, 4))
    elements.append(Paragraph("DE: Dirección de Operaciones e Inteligencia de Negocio", header_meta_style))
    elements.append(Paragraph("PARA: Comité Directivo y Gerencia General", header_meta_style))
    elements.append(Paragraph("ASUNTO: Dictamen Ejecutivo Integral de Inventarios, Mermas y Riesgo de Caducidad", header_meta_style))
    elements.append(Spacer(1, 6))
    
    cleaned_lines = []
    for line in texto_informe.split('\n'):
        if '|' in line and ('---' in line or 'SKU' in line or 'Producto' in line):
            continue
        clean_line = line.replace('**', '').replace('###', '').replace('|', ' ').strip()
        if clean_line:
            cleaned_lines.append(clean_line)
            
    for paragraph in cleaned_lines:
        p_text = paragraph.strip()
        if p_text and not p_text.startswith("DE:") and not p_text.startswith("PARA:") and not p_text.startswith("ASUNTO:"):
            es_subtitulo = (p_text.isupper() and len(p_text) > 3 or p_text.endswith(':') or any(k in p_text.upper() for k in ["RESUMEN", "HALLAZGOS", "DICTAMEN", "RECOMENDACIONES", "CRÍTICO", "ALERTAS", "DIAGNÓSTICO"]))
            if es_subtitulo:
                elements.append(Paragraph(p_text, heading_style))
            else:
                elements.append(Paragraph(p_text, body_style))
                
    elements.append(Spacer(1, 10))
    ancho_pagina_util = 540 
    
    for nombre, df in dfs_dict.items():
        elements.append(Paragraph(f"Muestra de Datos Auditados: {nombre.replace('_', ' ')}", heading_style))
        df_sample = df.head(5).fillna("")
        table_data = []
        header_row = [Paragraph(f"<b>{str(col).replace('_', ' ')}</b>", header_cell_style) for col in df_sample.columns]
        table_data.append(header_row)
        for _, row in df_sample.iterrows():
            row_data = [Paragraph(f"<b>{str(val)}</b>", cell_style) for val in row.values]
            table_data.append(row_data)
            
        num_cols = len(df_sample.columns)
        col_width = ancho_pagina_util / max(num_cols, 1)
        col_widths = [col_width] * num_cols
        
        t = Table(table_data, colWidths=col_widths)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0F172A')),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('BOTTOMPADDING', (0,0), (-1,0), 5),
            ('TOPPADDING', (0,0), (-1,0), 5),
            ('BACKGROUND', (0,1), (-1,-1), colors.HexColor('#F8FAFC')),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 10))
        
    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()

# --- DASHBOARD INICIAL (OBSERVABILIDAD CON DRILL-DOWN INTERACTIVO) ---
st.markdown("### 📊 Tableros de Control Operativo (Análisis Inicial del Sistema)")
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
    st.markdown("#### ⚠️ Distribución y Detalle de Alertas de Caducidad")
    
    selection = alt.selection_point(fields=['alerta_riesgo'], bind='legend')
    
    df_counts = df_riesgo_local['alerta_riesgo'].value_counts().reset_index()
    df_counts.columns = ['alerta_riesgo', 'Cantidad']
    
    categorias_orden = df_counts['alerta_riesgo'].tolist()
    colores_category10 = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']
    colores_asignados = colores_category10[:len(categorias_orden)]
    
    chart_risk = alt.Chart(df_counts).mark_arc(innerRadius=50).encode(
        theta=alt.Theta(field="Cantidad", type="quantitative"),
        color=alt.Color(
            field="alerta_riesgo", 
            type="nominal", 
            scale=alt.Scale(domain=categorias_orden, range=colores_asignados), 
            legend=alt.Legend(title="Haz clic o pasa el cursor")
        ),
        tooltip=['alerta_riesgo', 'Cantidad'],
        opacity=alt.condition(selection, alt.value(1), alt.value(0.3))
    ).add_params(selection).properties(height=300, width='container').interactive()
    
    st.altair_chart(chart_risk, use_container_width=True, theme="streamlit")

# --- BLOQUE CENTRAL DE FILTRO Y TABLA DE DETALLE ---
_, col_centro_detalle, _ = st.columns([0.15, 0.7, 0.15])
with col_centro_detalle:
    opciones_alerta = df_riesgo_local['alerta_riesgo'].unique().tolist()
    alerta_seleccionada = st.selectbox("🔎 O filtra el detalle de productos por tipo de alerta:", options=["(Ver todos los productos con riesgo)"] + opciones_alerta)
    
    if alerta_seleccionada != "(Ver todos los productos con riesgo)":
        df_detalle_filtrado = df_riesgo_local[df_riesgo_local['alerta_riesgo'] == alerta_seleccionada]
    else:
        df_detalle_filtrado = df_riesgo_local[df_riesgo_local['alerta_riesgo'] != 'Sin Riesgo']
        
    colores_mapa = dict(zip(categorias_orden, colores_asignados))
    
    def estilizar_filas_por_alerta(row):
        color_hex = colores_mapa.get(row['alerta_riesgo'], '#ffffff')
        return [f'background-color: {color_hex}; color: #0F172A; font-weight: bold;' if col == 'alerta_riesgo' else '' for col in row.index]

    df_estilizado = df_detalle_filtrado[['producto_id', 'nombre_producto', 'proveedor_principal', 'dias_para_vencer', 'alerta_riesgo']].style.apply(estilizar_filas_por_alerta, axis=1)
    
    st.dataframe(df_estilizado, use_container_width=True)

# --- CAJA DE BIENVENIDA Y PROMPT DINÁMICO ---
st.markdown("""
    <div class="welcome-box">
        <h4>🤖 El Agente Autónomo está listo para razonar:</h4>
        <p>El sistema detectó de forma preliminar anomalías severas en <b>Caracas Centro</b> y alertas críticas de caducidad. Ahora puedes interactuar directamente con el agente para ordenarle que ejecute herramientas de búsqueda y te elabore un informe gerencial profundo.</p>
    </div>
""", unsafe_allow_html=True)

user_prompt = st.text_area(
    "Instrucción para el Agente Autónomo:", 
    value="Realiza una auditoría integral invocando las herramientas necesarias para analizar las tiendas con mayores faltantes y las alertas de caducidad crítica.", 
    height=80
)

if st.button("🚀 Ejecutar Ciclo Autónomo del Agente", type="primary"):
    with st.spinner("🤖 El agente está analizando el entorno y decidiendo qué herramientas invocar (reintento automático transparente)..."):
        try:
            client = genai.Client(api_key=GEMINI_API_KEY)
            
            instruccion_maestra = """
            Eres un Agente Autónomo Senior de Auditoría Operativa y Retail de Sabertec.
            Tienes acceso a herramientas especializadas para consultar bases de datos de inventario, caducidades y ventas.
            Utiliza las herramientas disponibles de forma inteligente para recopilar la información exacta que responda a la solicitud del usuario.
            Una vez obtenida la información, redacta un dictamen ejecutivo de alto nivel gerencial para directores de finanzas y operaciones.
            Evita usar tablas con formato markdown complejo dentro de tu respuesta de texto, ya que la salida principal está diseñada para prosa ejecutiva estructurada en párrafos claros y directos.
            Reglas: No menciones que eres una IA basada en código Python; céntrate estrictamente en lenguaje gerencial, hallazgos y recomendaciones.
            """
            
            config = types.GenerateContentConfig(
                system_instruction=instruccion_maestra,
                tools=available_tools,
                temperature=0.2
            )
            
            # Se prioriza gemini-3.5-flash-lite para evitar saturar el límite de cuota gratuita diaria (429 quota exhausted)
            modelos_a_probar = ['gemini-3.5-flash-lite', 'gemini-3.6-flash']
            response = None
            exito = False
            ultimo_error = None
            
            for modelo in modelos_a_probar:
                if exito:
                    break
                for intento in range(3):
                    try:
                        chat = client.chats.create(model=modelo, config=config)
                        response = chat.send_message(user_prompt)
                        exito = True
                        break
                    except Exception as e:
                        ultimo_error = e
                        str_err = str(e)
                        if "429" in str_err or "RESOURCE_EXHAUSTED" in str_err or "503" in str_err or "UNAVAILABLE" in str_err:
                            time.sleep(2 * (intento + 1))
                            continue
                        else:
                            break # Si es otro error de código, salta al siguiente modelo
            
            if not exito:
                raise ultimo_error
            
            texto_limpio = response.text
            st.session_state['analisis_hecho'] = True
            st.session_state['informe_texto'] = texto_limpio
            st.session_state['pdf_data'] = create_clean_pdf(texto_limpio, dfs_fijos)
            st.rerun()
            
        except Exception as err:
            err_str = str(err)
            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                st.error("⚠️ Has alcanzado temporalmente el límite de solicitudes gratuitas de la API de Gemini (Error 429). El modelo se ha protegido contra bloqueos. Espera unos segundos o considera usar una clave de pago para pruebas masivas continuas.")
            else:
                st.error(f"⚠️ Ocurrió un error al procesar la solicitud con el agente. Detalle técnico: {err_str}")

# --- RESULTADOS Y SALIDAS ---
if st.session_state.get('analisis_hecho', False):
    st.success("✅ Ciclo de razonamiento autónomo completado con éxito.")
    st.markdown("### 📋 Dictamen de Auditoría del Agente")
    st.markdown(st.session_state['informe_texto'])
    st.markdown("---")
    st.markdown("### 📥 Exportar Reportes Oficiales")
    
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
            <h3>🚀 ¿Quieres desplegar este Agente Autónomo en la operación real de tu empresa?</h3>
            <p>Automatiza el control de mermas, conecta bases de datos SQL en vivo y potencia la toma de decisiones con Sabertec.</p>
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
                st.success(f"¡Excelente! Hemos registrado tu solicitud para el correo **{email_lead}**. Te contactaremos para coordinar la demo.")
            else:
                st.warning("Por favor ingresa un correo electrónico válido.")