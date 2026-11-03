from io import BytesIO
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from utils.anova_utils import (
	ajustar_dca,
	cargar_datos,
	coeficiente_variacion,
	f_critica,
	interpretar_dca,
	resumen_tratamientos,
	tabla_anova,
	tukey,
	validar_dca,
)
from utils.diagnostico_utils import (
	grafico_qq,
	grafico_residuos_vs_ajustados,
	prueba_levene,
	prueba_shapiro,
	residuos_y_ajustados,
)

ARCHIVO_EJEMPLO = Path(__file__).resolve().parents[1] / "data" / "dca_secadores.csv"


@st.cache_data(show_spinner=False)
def cargar_datos_cache(
	contenido: bytes | None, nombre_archivo: str
) -> pd.DataFrame:
	"""Carga y cachea el archivo del experimento.

	Args:
		contenido: Bytes del archivo cargado, o None para usar una ruta local.
		nombre_archivo: Nombre del archivo o ruta del conjunto de ejemplo.

	Returns:
		Los datos leídos desde CSV o Excel.
	"""
	if contenido is None:
		return cargar_datos(nombre_archivo)
	return cargar_datos(BytesIO(contenido), nombre_archivo)


st.title("Diseño Completamente al Azar (DCA)")
st.write(
	"El DCA compara tratamientos asignados al azar cuando las unidades experimentales "
	"son relativamente homogéneas. En este ejemplo se compara la humedad final de "
	"yuca secada en cuatro secadores solares, con cuatro réplicas por secador."
)

archivo_subido = st.file_uploader(
	"Carga los datos del experimento", type=["csv", "xlsx"]
)

try:
	if archivo_subido is None:
		datos = cargar_datos_cache(None, str(ARCHIVO_EJEMPLO))
		st.caption(
			"No se cargó un archivo; se usan los datos de ejemplo "
			"data/dca_secadores.csv."
		)
	else:
		datos = cargar_datos_cache(archivo_subido.getvalue(), archivo_subido.name)
except Exception as error:
	st.error(f"No fue posible leer el archivo: {error}")
	st.stop()

if datos.empty or len(datos.columns) == 0:
	st.error("El archivo no contiene datos ni columnas para analizar.")
	st.stop()

columnas = list(datos.columns)
columnas_numericas = list(datos.select_dtypes(include="number").columns)
indice_tratamiento = columnas.index("secador") if "secador" in columnas else 0
if "humedad" in columnas:
	indice_respuesta = columnas.index("humedad")
elif columnas_numericas:
	indice_respuesta = columnas.index(columnas_numericas[0])
else:
	indice_respuesta = 0

columna_tratamiento = st.selectbox(
	"Columna de tratamiento",
	columnas,
	index=indice_tratamiento,
	key="columna_tratamiento_dca",
)
columna_respuesta = st.selectbox(
	"Columna de respuesta",
	columnas,
	index=indice_respuesta,
	key="columna_respuesta_dca",
)
alfa = st.slider(
	"Nivel de significancia (alfa)",
	min_value=0.01,
	max_value=0.10,
	value=0.05,
	step=0.01,
)

errores = validar_dca(datos, columna_tratamiento, columna_respuesta)
if errores:
	for mensaje in errores:
		st.error(mensaje)
	st.stop()

try:
	modelo = ajustar_dca(datos, columna_tratamiento, columna_respuesta)
	tabla = tabla_anova(modelo)
	resumen = resumen_tratamientos(datos, columna_tratamiento, columna_respuesta)
	cv = coeficiente_variacion(modelo, datos, columna_respuesta)
	f_critico = f_critica(tabla, alfa)
	p_valor = float(
		tabla.loc[tabla["Fuente"] == "Tratamientos", "p-valor"].iloc[0]
	)
except (ValueError, TypeError, KeyError) as error:
	st.error(f"No fue posible analizar los datos: {error}")
	st.stop()

try:
	residuos, ajustados = residuos_y_ajustados(modelo)
	estadistico_shapiro, p_shapiro, conclusion_shapiro = prueba_shapiro(
		residuos, alfa
	)
	estadistico_levene, p_levene, conclusion_levene = prueba_levene(
		datos, columna_tratamiento, columna_respuesta, alfa
	)
except ValueError as error:
	st.error(f"No fue posible revisar los supuestos: {error}")
	st.stop()

tabla_supuestos = pd.DataFrame(
	[
		{
			"Prueba": "Shapiro-Wilk (normalidad)",
			"Estadístico": estadistico_shapiro,
			"p-valor": p_shapiro,
			"Conclusión": conclusion_shapiro,
		},
		{
			"Prueba": "Levene (homogeneidad de varianzas)",
			"Estadístico": estadistico_levene,
			"p-valor": p_levene,
			"Conclusión": conclusion_levene,
		},
	]
)

pestana_datos, pestana_anova, pestana_comparaciones, pestana_graficos, pestana_supuestos = st.tabs(
	["Datos", "ANOVA", "Comparaciones", "Gráficos", "Supuestos"]
)

with pestana_datos:
	st.subheader("Datos del experimento")
	st.dataframe(datos, width="stretch")
	st.subheader("Resumen por tratamiento")
	st.dataframe(resumen, width="stretch")

with pestana_anova:
	st.subheader("Análisis de varianza")
	st.dataframe(
		tabla.style.format(precision=4, na_rep="—"),
		width="stretch",
	)
	columna_f, columna_cv = st.columns(2)
	with columna_f:
		st.metric("F crítica", f"{f_critico:.4f}")
	with columna_cv:
		st.metric("Coeficiente de variación", f"{cv:.4f}%")

	interpretacion = interpretar_dca(tabla, alfa)
	if p_valor <= alfa:
		st.success(interpretacion)
	else:
		st.info(interpretacion)

with pestana_comparaciones:
	st.subheader("Comparaciones múltiples de Tukey")
	if p_valor < alfa:
		comparaciones, dms = tukey(
			datos, columna_tratamiento, columna_respuesta, alfa
		)
		if "aviso" in comparaciones.attrs:
			st.warning(comparaciones.attrs["aviso"])
		st.dataframe(
			comparaciones.style.format(precision=4, na_rep="—"),
			width="stretch",
		)
		st.write(f"Diferencia mínima significativa (DMS): **{dms:.4f}**")
	else:
		st.info(
			f"No se realizan comparaciones de Tukey porque el ANOVA no detectó "
			f"diferencias significativas (p = {p_valor:.4f} no es menor que "
			f"alfa = {alfa:.2f})."
		)

with pestana_graficos:
	st.subheader("Distribución de la respuesta por tratamiento")
	figura_cajas = px.box(
		datos,
		x=columna_tratamiento,
		y=columna_respuesta,
		points="all",
		labels={
			columna_tratamiento: "Tratamiento",
			columna_respuesta: "Respuesta",
		},
		title="Respuesta por tratamiento",
	)
	st.plotly_chart(figura_cajas, width="stretch")

	st.subheader("Media por tratamiento")
	figura_medias = px.bar(
		resumen,
		x=columna_tratamiento,
		y="media",
		error_y="desviación estándar",
		labels={
			columna_tratamiento: "Tratamiento",
			"media": "Media de la respuesta",
			"desviación estándar": "Desviación estándar",
		},
		title="Media y desviación estándar por tratamiento",
	)
	st.plotly_chart(figura_medias, width="stretch")

with pestana_supuestos:
	st.subheader("Diagnóstico de supuestos del DCA")
	st.write(
		"Shapiro-Wilk revisa si los residuos son compatibles con una distribución normal. "
		"Levene, centrada en la mediana, revisa si la variabilidad de la respuesta es "
		"similar entre tratamientos."
	)
	st.dataframe(
		tabla_supuestos.style.format(
			{"Estadístico": "{:.4f}", "p-valor": "{:.4f}"}, na_rep="—"
		),
		width="stretch",
	)
	st.plotly_chart(
		grafico_residuos_vs_ajustados(ajustados, residuos), width="stretch"
	)
	st.plotly_chart(grafico_qq(residuos), width="stretch")
	st.info(
		"Independencia: se sustenta en la asignación aleatoria de los tratamientos y "
		"en que las unidades experimentales sean independientes. Shapiro-Wilk y Levene "
		"no prueban independencia; esta condición se justifica con el protocolo y la "
		"ejecución del experimento."
	)
