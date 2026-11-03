AUTOR = "Escribe aquí tu nombre"

import streamlit as st

st.set_page_config(
    page_title="App de Diseño Experimental",
    page_icon="🌱",
    layout="wide",
)

st.title("App de Diseño Experimental")
st.subheader("Ingeniería Agrícola – Universidad de Sucre")
st.write(
    "El diseño experimental permite planear comparaciones confiables entre "
    "tratamientos agrícolas, reducir la influencia de fuentes de variación "
    "ajenas al estudio y tomar decisiones basadas en evidencia obtenida en campo."
)

modulos = [
    {
        "Módulo": "DCA",
        "Nombre completo": "Diseño Completamente al Azar",
        "Cuándo se usa": "Cuando las unidades experimentales son homogéneas y los tratamientos se asignan al azar.",
        "Ejemplo agrícola": "Comparar dosis de fertilizante en parcelas de suelo uniforme.",
        "Estado": "Disponible",
    },
    {
        "Módulo": "DBCA",
        "Nombre completo": "Diseño en Bloques Completos al Azar",
        "Cuándo se usa": "Cuando se necesita controlar una fuente de variación agrupando unidades similares en bloques.",
        "Ejemplo agrícola": "Comparar variedades de maíz en bloques distribuidos a lo largo de una pendiente.",
        "Estado": "En construcción",
    },
    {
        "Módulo": "DCL",
        "Nombre completo": "Diseño de Cuadrado Latino",
        "Cuándo se usa": "Cuando se deben controlar dos fuentes de variación mediante filas y columnas.",
        "Ejemplo agrícola": "Comparar variedades de fríjol controlando gradientes de suelo y riego.",
        "Estado": "En construcción",
    },
    {
        "Módulo": "DPD",
        "Nombre completo": "Diseño de Parcelas Divididas",
        "Cuándo se usa": "Cuando los factores se asignan en dos niveles de unidades experimentales.",
        "Ejemplo agrícola": "Evaluar sistemas de riego en parcelas principales y variedades en subparcelas.",
        "Estado": "En construcción",
    },
    {
        "Módulo": "Factoriales",
        "Nombre completo": "Diseños Factoriales",
        "Cuándo se usa": "Cuando se estudian dos o más factores y sus posibles interacciones.",
        "Ejemplo agrícola": "Evaluar conjuntamente dosis de nitrógeno y láminas de riego en maíz.",
        "Estado": "En construcción",
    },
    {
        "Módulo": "RSM",
        "Nombre completo": "Metodología de Superficie de Respuesta",
        "Cuándo se usa": "Cuando se busca optimizar una respuesta en función de factores cuantitativos.",
        "Ejemplo agrícola": "Encontrar la combinación de fertilizante y agua que favorece el rendimiento del tomate.",
        "Estado": "En construcción",
    },
]

st.subheader("Módulos")
st.table(modulos)

st.subheader("Cómo usar la aplicación")
st.markdown(
    "1. Elige un módulo en el menú lateral.\n"
    "2. Carga los datos del experimento.\n"
    "3. Revisa e interpreta los resultados.\n"
    "4. Verifica los resultados a mano y contrástalos con tus cálculos."
)

st.warning(
    "Esta app apoya el aprendizaje. El estudiante interpreta los resultados, "
    "verifica supuestos y compara con su cálculo manual."
)

st.sidebar.header("Información del curso")
st.sidebar.write(f"Autor: {AUTOR}")
st.sidebar.write("Curso: Diseño Experimental")
st.sidebar.write("Semestre: 2026-2")
