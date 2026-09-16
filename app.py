
import matplotlib.pyplot as plt
import pandas as pd
import requests
import streamlit as st

BASE_URL = "http://localhost:8080"
TASA_GLOBAL = 0.224
UMBRAL_MODELO = 0.228

#traducción para app
EMP_LENGTH = {
    "Menos de 1 año": "< 1 year",
    "1 año": "1 year",
    "2 años": "2 years",
    "3 años": "3 years",
    "4 años": "4 years",
    "5 años": "5 years",
    "6 años": "6 years",
    "7 años": "7 years",
    "8 años": "8 years",
    "9 años": "9 years",
    "10 años o más": "10+ years",
    "No informado": "NI",
}

PURPOSE = {
    "Consolidación de deuda": "debt_consolidation",
    "Tarjeta de crédito": "credit_card",
    "Reforma del hogar": "home_improvement",
    "Otro": "other",
    "Compra importante": "major_purchase",
    "Gastos médicos": "medical",
    "Coche": "car",
    "Pequeño negocio": "small_business",
    "Vacaciones": "vacation",
    "Mudanza": "moving",
    "Vivienda": "house",
    "Energía renovable": "renewable_energy",
    "Boda": "wedding",
}

HOME_OWNERSHIP = {
    "Hipoteca": "MORTGAGE",
    "Alquiler": "RENT",
    "Vivienda en propiedad": "OWN",
    "Otra situación": "OTHER",
}

ESTADOS = [
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "DC", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA",
    "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY",
    "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", "SD", "TN", "TX",
    "UT", "VT", "VA", "WA", "WV", "WI", "WY",
]

NOMBRES = {
    "revenue": "Ingresos anuales",
    "dti_n": "Ratio deuda/ingresos",
    "loan_amnt": "Importe solicitado",
    "fico_n": "Puntuación FICO",
    "emp_length": "Antigüedad laboral",
    "home_ownership_n": "Situación de vivienda",
    "purpose": "Finalidad del préstamo",
    "addr_state": "Estado de residencia",
}


#LLAMADAS

def llamar_api(ruta, datos):
    """Envía una petición a la API y controla los posibles errores."""
    try:
        respuesta = requests.post(
            f"{BASE_URL}/{ruta}",
            json=datos,
            timeout=30
        )

        try:
            contenido = respuesta.json()
        except requests.exceptions.JSONDecodeError:
            contenido = None

        if not respuesta.ok:
            if isinstance(contenido, dict):
                detalle = contenido.get("error", str(contenido))
            else:
                detalle = respuesta.text.strip() or respuesta.reason

            return False, (
                f"La API devolvió el código "
                f"{respuesta.status_code}: {detalle}"
            )

        if contenido is None:
            return False, (
                "La API respondió, pero el contenido recibido "
                "no se encontraba en formato JSON."
            )
        return True, contenido

    except requests.exceptions.ConnectionError:
        return False, (
            "No se puede conectar con Flask. Comprueba que "
            "el servicio está ejecutándose en el puerto 8080."
        )
    except requests.exceptions.Timeout:
        return False, (
            "La API ha tardado demasiado tiempo en responder."
        )
    except requests.exceptions.RequestException as error:
        return False, (
            f"No se pudo completar la petición: {error}"
        )



def texto_variable(nombre):
    """Traduce SHAP a espanol."""
    if " = " in nombre:
        columna, valor = nombre.split(" = ", 1)
        diccionario = {"emp_length": EMP_LENGTH, "purpose": PURPOSE,
                       "home_ownership_n": HOME_OWNERSHIP}.get(columna, {})
        valor_es = {v: k for k, v in diccionario.items()}.get(valor, valor)
        return f"{NOMBRES.get(columna, columna)} = {valor_es}"
    return NOMBRES.get(nombre, nombre)


def texto_valor(clave, valor):
    """Formatea el valor enviado a la API para mostrarlo en el expediente."""
    if clave == "emp_length":
        return {v: k for k, v in EMP_LENGTH.items()}.get(valor, valor)
    if clave == "purpose":
        return {v: k for k, v in PURPOSE.items()}.get(valor, valor)
    if clave == "home_ownership_n":
        return {v: k for k, v in HOME_OWNERSHIP.items()}.get(valor, valor)
    if clave in ("revenue", "loan_amnt"):
        return f"{valor:,.0f} $".replace(",", ".")
    if clave == "dti_n":
        return f"{valor:.1f} %"
    if clave == "fico_n":
        return f"{valor:.0f} puntos"
    return valor



def grafico_pistas(factores):
    """Contribuciones SHAP """
    tabla = pd.DataFrame(factores).sort_values("efecto_shap", key=abs)
    tabla["variable"] = tabla["variable"].apply(texto_variable)
    colores = ["firebrick" if valor > 0 else "steelblue" for valor in tabla["efecto_shap"]]

    fig, ax = plt.subplots(figsize=(7.2, 0.55 * len(tabla) + 1.2))
    ax.barh(tabla["variable"], tabla["efecto_shap"], color=colores, height=0.6)
    ax.axvline(0, color="lightsteelblue", linewidth=1)
    ax.set_xlabel("Contribución a la estimación", fontsize=8.5, color="slategray")
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color("lightsteelblue")
    ax.tick_params(colors="slategray", labelsize=8.5)
    fig.tight_layout()
    return fig


def grafico_segmento(tasa_segmento, tasa_global):
    """Compara la tasa de impago del segmento con la de toda la cartera."""
    valores = [tasa_segmento * 100, tasa_global * 100]
    color_segmento = "firebrick" if tasa_segmento > tasa_global else "seagreen"

    fig, ax = plt.subplots(figsize=(4.6, 2.6))
    barras = ax.bar(["Este segmento", "Toda la cartera"], valores,
                    color=[color_segmento, "lightsteelblue"], width=0.55)
    for barra, valor in zip(barras, valores):
        ax.text(barra.get_x() + barra.get_width() / 2, valor + 1.2, f"{valor:.1f}%",
                ha="center", fontsize=9.5, color="darkslategray", fontweight="bold")
    ax.set_ylabel("Tasa histórica de impago (%)", fontsize=8.5, color="slategray")
    ax.set_ylim(0, max(valores) * 1.35)
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color("lightsteelblue")
    ax.tick_params(colors="slategray", labelsize=9)
    fig.tight_layout()
    return fig


# Configuracion de la pagina 

st.set_page_config(page_title="Bajo la Lupa", page_icon="🕵️", layout="wide")

st.markdown(
    '<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/'
    'font-awesome/6.5.1/css/all.min.css">',
    unsafe_allow_html=True,
)

st.markdown("""
    <style>
    .stApp { background-color: mintcream; }
    .block-container { max-width: 1080px; padding-top: 1.6rem; padding-bottom: 3rem; }
    h1, h2, h3 { color: darkslategray; }

    .marca { display: flex; align-items: center; gap: 0.55rem; }
    .marca span:first-child { font-size: 2.3rem; }
    .marca span:last-child { font-size: 1.35rem; font-weight: 700; color: darkslategray; }

    .tarjeta {
        background-color: white;
        border: 1px solid aliceblue;
        border-radius: 14px;
        padding: 1.3rem 1.4rem;
        box-shadow: 0 2px 10px lightgray;
        margin-bottom: 1rem;
    }

    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-color: aliceblue !important;
        border-radius: 14px !important;
        background-color: white;
        box-shadow: 0 2px 10px lightgray;
    }

    .stButton > button {
        border-radius: 10px;
        border: 1px solid aliceblue;
        font-weight: 600;
        padding: 0.55rem 1.4rem;
        background-color: white;
        color: darkslategray;
    }
    .stButton > button:hover { border-color: cornflowerblue; color: steelblue; }
    .stButton > button[kind="primary"] {
        background-color: steelblue; border: none; color: white;
    }
    .stButton > button[kind="primary"]:hover { background-color: darkslategray; }

    div[data-baseweb="select"] > div, .stNumberInput input { border-radius: 8px !important; }
    section[data-testid="stSidebar"] { background-color: aliceblue; }

    .veredicto-ok {
        background-color: honeydew; border-left: 4px solid seagreen;
        border-radius: 8px; padding: 0.9rem 1.1rem; color: darkgreen;
    }
    .veredicto-alerta {
        background-color: mistyrose; border-left: 4px solid firebrick;
        border-radius: 8px; padding: 0.9rem 1.1rem; color: saddlebrown;
    }

    .circulo {
        border-radius: 50%; display: flex; align-items: center; justify-content: center;
        width: 84px; height: 84px; margin: 0 auto 0.7rem;
        background-color: aliceblue;
        box-shadow: 0 3px 12px lightgray;
    }
    .circulo i { font-size: 1.9rem; color: steelblue; }
    .circulo-azul { background-color: steelblue; width: 120px; height: 120px; }
    .circulo-azul i { font-size: 2.6rem; color: white; }

   
    .circulo-probabilidad {
        width: 168px; height: 168px; border-radius: 50%; border: 6px solid;
        display: flex; flex-direction: column; align-items: center; justify-content: center;
        margin: 0 auto; box-shadow: 0 4px 16px lightgray;
    }
    .circulo-probabilidad .valor { font-size: 2rem; font-weight: 800; line-height: 1; }
    .circulo-probabilidad .etiqueta {
        font-size: 0.72rem; text-align: center; margin-top: 0.35rem; max-width: 7.5rem;
    }

    @keyframes mover-lupa {
        0%, 100% { transform: translate(0, 0) rotate(0deg); }
        25% { transform: translate(3px, -2px) rotate(-8deg); }
        50% { transform: translate(-2px, 2px) rotate(6deg); }
        75% { transform: translate(2px, 1px) rotate(-4deg); }
    }
    .lupa-animada { display: inline-block; animation: mover-lupa 1.6s ease-in-out infinite; }

    @keyframes flotar {
        0%, 100% { transform: translateY(0) rotate(0deg); }
        50% { transform: translateY(-10px) rotate(-6deg); }
    }
    .billete { display: inline-block; margin: 0 0.25rem; animation: flotar 1s ease-in-out infinite; }

    
    .silueta {
        position: fixed; top: 50%; transform: translateY(-50%);
        font-size: 13rem; color: darkslategray; opacity: 0.05;
        pointer-events: none; z-index: 0; line-height: 1;
    }
    .silueta-izquierda { left: 13rem; }
    .silueta-derecha { right: 13rem; transform: translateY(-50%) scaleX(-1); }
    .silueta-izquierda.con-menu { left: 22rem; }
    .silueta-derecha.con-menu { right: 4rem; }
    @media (max-width: 1400px) { .silueta { display: none; } }

    .titulo-con-icono { display:flex; align-items:center; gap:0.6rem; margin-bottom:0.8rem; }
    .icono-tarjeta { width:38px; height:38px; margin:0; }
    .texto-titulo-tarjeta { color:steelblue; font-weight:700; }
    .tarjeta-agente { background-color:aliceblue; border:none; margin-top:1rem; }
    .titulo-agente { display:flex; align-items:center; gap:0.5rem; margin-bottom:0.5rem; }
    .texto-agente { color:darkslategray; margin:0; line-height:1.5; }
    .tarjeta-dato { padding:0.8rem 1rem; margin-bottom:0.6rem; }
    .etiqueta-dato { color:slategray; font-size:0.78rem; }
    .valor-dato { color:darkslategray; font-weight:600; }
    .tarjeta-segmento { display:flex; align-items:center; gap:1rem; }
    </style>
""", unsafe_allow_html=True)


def marca():
    st.markdown("<div class='marca'><span>🔎</span><span>Bajo la Lupa</span></div>",
                unsafe_allow_html=True)


def siluetas(con_menu=False):
    """Detectives de fondo. Con el menu lateral abierto se apartan para no taparse."""
    clase = " con-menu" if con_menu else ""
    st.markdown(
        f"<i class='fa-solid fa-user-secret silueta silueta-izquierda{clase}'></i>"
        f"<i class='fa-solid fa-user-secret silueta silueta-derecha{clase}'></i>",
        unsafe_allow_html=True,
    )


if "pantalla" not in st.session_state:
    st.session_state.pantalla = "portada"
if "resultado" not in st.session_state:
    st.session_state.resultado = None


def ir_a(pantalla):
    st.session_state.pantalla = pantalla
    st.rerun()

def menu_lateral():
    with st.sidebar:
        marca()
        st.caption("Detector de riesgo")
        st.divider()
        if st.button("Inicio", use_container_width=True):
            ir_a("portada")
        if st.button("Nueva investigación", use_container_width=True):
            ir_a("formulario")


def pantalla_portada():
    siluetas()
    st.markdown("<div style='height: 4vh'></div>", unsafe_allow_html=True)

    with st.columns([1, 2.4, 1])[1]:
        st.markdown("""
            <div style='position:relative; display:flex; align-items:center;
                        justify-content:center; gap:1.1rem; margin-bottom:1rem;'>
              <span style='position:absolute; left:6%; top:-10px; font-size:1.6rem;
                           transform:rotate(-18deg);'>💵</span>
              <span style='position:absolute; right:8%; top:0; font-size:1.3rem;
                           transform:rotate(12deg);'>💶</span>
              <div class='circulo' style='width:76px; height:76px; margin:0;'>
                <i class="fa-solid fa-user-secret"></i></div>
              <div class='circulo circulo-azul'>
                <i class="fa-solid fa-magnifying-glass-dollar"></i></div>
              <div class='circulo' style='width:76px; height:76px; margin:0;'>
                <i class="fa-solid fa-sack-dollar"></i></div>
              <span style='position:absolute; right:16%; bottom:-8px; font-size:1.2rem;
                           transform:rotate(-10deg);'>💶</span>
            </div>

            <h1 style='text-align:center; margin-bottom:0.1rem; text-transform:uppercase;
                       letter-spacing:0.04em; font-size:3rem; color:darkslategray;'>Bajo la Lupa</h1>
            <p style='text-align:center; color:steelblue; font-size:1.15rem;
                      font-weight:600; margin-top:0;'>Detector de riesgo</p>
            <p style='text-align:center; color:slategray; font-size:1rem;
                      max-width:34rem; margin:0.6rem auto 0;'>
              🕵️ Rellena unos datos y descubre el riesgo del préstamo.</p>

            <div style='display:flex; justify-content:center; gap:0.6rem;
                        margin:2.6vh auto 1.8rem; max-width:36rem;'>
              <div style='text-align:center; flex:1;'>
                <div style='font-size:2rem;'>📝</div>
                <div style='color:darkslategray; font-weight:600; font-size:0.85rem;'>Rellenas los datos</div>
              </div>
              <div style='color:lightsteelblue; font-size:1.4rem; margin-top:0.6rem;'>→</div>
              <div style='text-align:center; flex:1;'>
                <div style='font-size:2rem;'>🔎</div>
                <div style='color:darkslategray; font-weight:600; font-size:0.85rem;'>Lo investigamos</div>
              </div>
              <div style='color:lightsteelblue; font-size:1.4rem; margin-top:0.6rem;'>→</div>
              <div style='text-align:center; flex:1;'>
                <div style='font-size:2rem;'>✅</div>
                <div style='color:darkslategray; font-weight:600; font-size:0.85rem;'>Ves el resultado</div>
              </div>
            </div>
        """, unsafe_allow_html=True)

        _, col_lupa, col_boton, _ = st.columns([1, 0.28, 1.4, 1])
        with col_lupa:
            st.markdown("<div style='display:flex; align-items:center; justify-content:center;"
                        "height:100%; font-size:1.7rem;'><span class='lupa-animada'>🔍</span></div>",
                        unsafe_allow_html=True)
        with col_boton:
            if st.button("Analizar una solicitud", type="primary", use_container_width=True):
                ir_a("formulario")


# formulario

def titulo_tarjeta(icono, texto):
    st.markdown(
        f"<div class='titulo-con-icono'>"
        f"<div class='circulo icono-tarjeta'>"
        f"<i class='fa-solid {icono}' style='font-size:1rem;'></i></div>"
        f"<span class='texto-titulo-tarjeta'>{texto}</span></div>",
        unsafe_allow_html=True,
    )


def pantalla_formulario():
    siluetas(con_menu=True)
    marca()
    st.title("🕵️ Nueva investigación")
    st.caption("Cada dato aporta una pista. Introduce la información de la solicitud.")

    with st.form("investigacion"):
        col_a, col_b, col_c = st.columns(3, gap="medium")

        with col_a, st.container(border=True):
            titulo_tarjeta("fa-sack-dollar", "Datos económicos")
            revenue = st.number_input("Ingresos anuales ($)", min_value=2000,
                                      value=50000, step=1000)
            loan_amnt = st.number_input("Importe solicitado ($)", min_value=1000,
                                        max_value=40000, value=12000, step=500)
            dti_n = st.number_input("Ratio deuda/ingresos (%)", min_value=0.0,
                                    max_value=150.0, value=20.0, step=0.5)

        with col_b, st.container(border=True):
            titulo_tarjeta("fa-user-secret", "Perfil del solicitante")
            fico_n = st.number_input("Puntuación FICO", min_value=662.0,
                                     max_value=850.0, value=690.0, step=1.0)
            emp_length = st.selectbox("Antigüedad laboral", list(EMP_LENGTH), index=10)
            home_ownership_n = st.selectbox("Situación de vivienda", list(HOME_OWNERSHIP), index=0)

        with col_c, st.container(border=True):
            titulo_tarjeta("fa-file-signature", "Datos de la solicitud")
            purpose = st.selectbox("Finalidad del préstamo", list(PURPOSE), index=0)
            addr_state = st.selectbox("Estado de residencia", ESTADOS, index=4)

        _, col_boton, _ = st.columns([1, 1.2, 1])
        with col_boton:
            enviado = st.form_submit_button("🔎 Examinar solicitud", type="primary",
                                            use_container_width=True)

    if enviado:
        st.session_state.entrada = {
            "revenue": revenue,
            "dti_n": dti_n,
            "loan_amnt": loan_amnt,
            "fico_n": fico_n,
            "emp_length": EMP_LENGTH[emp_length],
            "purpose": PURPOSE[purpose],
            "home_ownership_n": HOME_OWNERSHIP[home_ownership_n],
            "addr_state": addr_state,
        }
        st.session_state.resultado = None
        ir_a("resultado")


# resultado

def consultar_api(entrada):
    """Consulta la predicción, el segmento y el agente, y devuelve sus respuestas."""
    cargando = st.empty()
    cargando.markdown("""
        <div style='text-align:center; padding:1.2rem 0;'>
          <div style='font-size:2.4rem;'>
            <span class='billete'>💵</span>
            <span class='billete' style='animation-delay:0.2s;'>💶</span>
            <span class='billete' style='animation-delay:0.4s;'>💵</span>
          </div>
          <p style='color:slategray; font-size:0.95rem;'>Investigando la solicitud…</p>
        </div>
    """, unsafe_allow_html=True)

    exito_pred, prediccion = llamar_api("explicar", entrada)
    exito_cluster, cluster = llamar_api("cluster", entrada)
    exito_agente, agente = llamar_api("agente_explicacion", entrada)
    cargando.empty()

    return {"exito_pred": exito_pred, "prediccion": prediccion,
            "exito_cluster": exito_cluster, "cluster": cluster,
            "exito_agente": exito_agente, "agente": agente}


def tarjeta_dato(titulo, valor):
    """Muestra un dato del expediente con el mismo formato en todas las tarjetas."""
    st.markdown(
        f"<div class='tarjeta tarjeta-dato'>"
        f"<div class='etiqueta-dato'>{titulo}</div>"
        f"<div class='valor-dato'>{valor}</div></div>",
        unsafe_allow_html=True,
    )


def pantalla_resultado():
    marca()
    entrada = st.session_state.get("entrada")
    if entrada is None:
        st.warning("No hay ninguna solicitud en curso.")
        if st.button("Ir a Nueva investigación"):
            ir_a("formulario")
        return

    if st.session_state.resultado is None:
        st.session_state.resultado = consultar_api(entrada)
    resultado = st.session_state.resultado

    if not resultado["exito_pred"]:
        st.error(resultado["prediccion"])
        if st.button("Volver a Nueva investigación"):
            st.session_state.resultado = None
            ir_a("formulario")
        return

    probabilidad = resultado["prediccion"]["probabilidad_impago"]
    supera_umbral = probabilidad >= UMBRAL_MODELO
    color = "firebrick" if supera_umbral else "seagreen"

    st.title("📋 Análisis completado")

    col_circulo, col_veredicto = st.columns(2, gap="large")
    with col_circulo:
        st.markdown(
            f"<div class='circulo-probabilidad' style='border-color:{color}; color:{color};'>"
            f"<span class='valor'>{probabilidad:.1%}</span>"
            f"<span class='etiqueta'>probabilidad estimada de impago</span></div>"
            f"<p style='text-align:center; color:slategray; font-size:0.85rem; margin-top:0.6rem;'>"
            f"Umbral de referencia: {UMBRAL_MODELO:.1%}</p>",
            unsafe_allow_html=True,
        )

    with col_veredicto:
        st.markdown(f"<div style='text-align:center; font-size:3.4rem;'>"
                    f"{'😟🕵️' if supera_umbral else '😊🕵️'}</div>", unsafe_allow_html=True)
        if supera_umbral:
            st.markdown("<div class='veredicto-alerta'>⚠ <strong>Señal de riesgo detectada</strong>"
                        "<br>El riesgo estimado alcanza o supera el umbral del modelo.</div>",
                        unsafe_allow_html=True)
        else:
            st.markdown("<div class='veredicto-ok'>✓ <strong>No se detecta una señal de riesgo"
                        "</strong><br>El riesgo estimado queda por debajo del umbral.</div>",
                        unsafe_allow_html=True)

    if resultado["exito_agente"]:
        st.markdown(
            f"<div class='tarjeta tarjeta-agente'>"
            f"<div class='titulo-agente'>"
            f"<span style='font-size:1.3rem;'>🕵️‍♀️💬</span>"
            f"<span class='texto-titulo-tarjeta'>Lectura del caso</span></div>"
            f"<p class='texto-agente'>"
            f"{resultado['agente']['explicacion']}</p></div>",
            unsafe_allow_html=True,
        )

    st.subheader("🔎 Analizamos la pista")
    st.caption("Factores que más han influido en la estimación de este caso.")
    st.pyplot(grafico_pistas(resultado["prediccion"]["factores"]), clear_figure=True)
    st.caption("Los factores positivos aumentan el riesgo estimado y los negativos lo reducen. "
               "Son asociaciones aprendidas por el modelo, no relaciones causales.")

    st.subheader("Resumen del expediente")
    columnas = st.columns(4)
    for i, (clave, valor) in enumerate(entrada.items()):
        with columnas[i % 4]:
            tarjeta_dato(NOMBRES[clave], texto_valor(clave, valor))

    if resultado["exito_cluster"]:
        cluster = resultado["cluster"]
        color_segmento = "firebrick" if cluster["tasa_impago_segmento"] > TASA_GLOBAL else "seagreen"
        st.markdown(
            f"<div class='tarjeta tarjeta-segmento'>"
            f"<div style='width:58px; height:58px; border-radius:50%; flex-shrink:0;"
            f"display:flex; align-items:center; justify-content:center;"
            f"background-color:{color_segmento};'>"
            f"<i class='fa-solid fa-user-tag' style='font-size:1.5rem; color:white;'></i></div>"
            f"<div><div style='color:slategray; font-size:0.78rem; text-transform:uppercase;'>"
            f"Perfil del cliente</div>"
            f"<div style='color:darkslategray; font-weight:800; font-size:1.3rem;'>"
            f"{cluster['nombre_segmento']}</div></div></div>",
            unsafe_allow_html=True,
        )
        with st.expander("Ver contexto de cartera para este segmento"):
            st.pyplot(grafico_segmento(cluster["tasa_impago_segmento"], TASA_GLOBAL),
                      clear_figure=True)
            st.caption("Tasa histórica del segmento, no una probabilidad para este caso.")

    with st.expander("Detalle técnico"):
        st.markdown("**Datos enviados a la API**")
        st.json(entrada)
        st.markdown("**Respuesta del modelo**")
        st.json(resultado["prediccion"])

    col_izq, col_der = st.columns(2)
    with col_izq:
        if st.button("🔎 Nueva investigación", use_container_width=True):
            st.session_state.resultado = None
            ir_a("formulario")
    with col_der:
        if st.button("Ir a Inicio", use_container_width=True):
            ir_a("portada")


if st.session_state.pantalla == "portada":
    pantalla_portada()
else:
    menu_lateral()
    if st.session_state.pantalla == "formulario":
        pantalla_formulario()
    elif st.session_state.pantalla == "resultado":
        pantalla_resultado()
    else:
        ir_a("portada")
