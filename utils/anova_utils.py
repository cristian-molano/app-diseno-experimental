"""Funciones reutilizables para analizar un Diseño Completamente al Azar."""

import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import studentized_range
from statsmodels.formula.api import ols
from statsmodels.regression.linear_model import RegressionResultsWrapper
from statsmodels.stats.anova import anova_lm
from statsmodels.stats.multicomp import pairwise_tukeyhsd


def cargar_datos(archivo: str | Path) -> pd.DataFrame:
    """Lee datos desde un archivo CSV o Excel.

    Args:
        archivo: Ruta de un archivo CSV o Excel con extensión `.xlsx`.

    Returns:
        Un DataFrame con los datos del archivo.

    Raises:
        ValueError: Si la extensión no corresponde a CSV o Excel `.xlsx`.
    """
    ruta = Path(archivo)

    # Paso 1: se elige el lector según la extensión; para CSV se detecta , o ;.
    # Regla de lectura: .csv -> sep=None; .xlsx -> lector de Excel.
    if ruta.suffix.lower() == ".csv":
        return pd.read_csv(ruta, sep=None, engine="python")
    if ruta.suffix.lower() == ".xlsx":
        return pd.read_excel(ruta)

    raise ValueError("El archivo debe tener extensión .csv o .xlsx.")


def validar_dca(df: pd.DataFrame, col_trat: str, col_resp: str) -> list[str]:
    """Valida los datos básicos requeridos para un DCA de un factor.

    Args:
        df: Datos del experimento.
        col_trat: Nombre de la columna que identifica los tratamientos.
        col_resp: Nombre de la columna con la respuesta numérica.

    Returns:
        Mensajes de error en español; una lista vacía indica que los datos
        cumplen las condiciones básicas del DCA.
    """
    errores: list[str] = []

    # Paso 1: se comprueba que existan las columnas necesarias antes de usarlas.
    columnas_faltantes = [
        nombre for nombre in (col_trat, col_resp) if nombre not in df.columns
    ]
    if columnas_faltantes:
        return [f"Falta la columna requerida: '{nombre}'." for nombre in columnas_faltantes]

    if col_trat == col_resp:
        return ["Las columnas de tratamiento y respuesta deben ser diferentes."]

    # Paso 2: los faltantes se revisan en las variables que definen el análisis.
    if df[[col_trat, col_resp]].isna().any().any():
        errores.append("Hay datos faltantes en las columnas de tratamiento o respuesta.")

    # Paso 3: se detectan textos que no pueden convertirse en una respuesta numérica.
    respuesta_numerica = pd.to_numeric(df[col_resp], errors="coerce")
    valores_no_numericos = respuesta_numerica.isna() & df[col_resp].notna()
    if valores_no_numericos.any():
        errores.append("La columna de respuesta debe contener valores numéricos.")

    # Paso 4: k es el número de tratamientos distintos y n_i el número de réplicas por tratamiento.
    numero_tratamientos = df[col_trat].nunique(dropna=True)
    if numero_tratamientos < 2:
        errores.append("El DCA requiere al menos dos tratamientos.")

    replicas_por_tratamiento = df.groupby(col_trat, dropna=True).size()
    tratamientos_con_pocas_replicas = replicas_por_tratamiento[
        replicas_por_tratamiento < 2
    ]
    for tratamiento in tratamientos_con_pocas_replicas.index:
        errores.append(
            f"El tratamiento '{tratamiento}' tiene menos de dos réplicas."
        )

    return errores


def ajustar_dca(
    df: pd.DataFrame, col_trat: str, col_resp: str
) -> RegressionResultsWrapper:
    """Ajusta el modelo lineal de un DCA con un factor.

    Args:
        df: Datos del experimento.
        col_trat: Nombre de la columna que identifica los tratamientos.
        col_resp: Nombre de la columna con la respuesta.

    Returns:
        El modelo OLS ajustado.

    Raises:
        ValueError: Si los datos no cumplen las validaciones básicas del DCA.
    """
    # Paso 1: se detiene el ajuste si faltan tratamientos, réplicas o respuestas válidas.
    errores = validar_dca(df, col_trat, col_resp)
    if errores:
        raise ValueError("No se puede ajustar el DCA: " + " ".join(errores))

    # Paso 2: se prepara una copia con la respuesta numérica para evitar alterar el DataFrame original.
    datos = df[[col_trat, col_resp]].copy()
    datos[col_resp] = pd.to_numeric(datos[col_resp], errors="raise")

    # Fórmula del DCA: Y_ij = μ + τ_i + ε_ij; Q protege nombres y C trata el factor como categórico.
    nombre_respuesta = json.dumps(col_resp, ensure_ascii=False)
    nombre_tratamiento = json.dumps(col_trat, ensure_ascii=False)
    formula = f"Q({nombre_respuesta}) ~ C(Q({nombre_tratamiento}))"

    # Paso 3: OLS estima la media general y los efectos de tratamiento indicados en la fórmula.
    return ols(formula, data=datos).fit()


def tabla_anova(modelo: RegressionResultsWrapper) -> pd.DataFrame:
    """Construye la tabla ANOVA tipo II e incluye la fila de total.

    Args:
        modelo: Modelo OLS ajustado para un DCA.

    Returns:
        Tabla con las columnas Fuente, gl, SC, CM, F y p-valor.
    """
    # Paso 1: ANOVA tipo II separa la variación atribuible a tratamientos y al error.
    tabla = anova_lm(modelo, typ=2).copy()
    tabla.index = [
        "Error" if str(fuente).lower() == "residual" else "Tratamientos"
        for fuente in tabla.index
    ]
    tabla = tabla.rename(
        columns={
            "df": "gl",
            "sum_sq": "SC",
            "PR(>F)": "p-valor",
        }
    )

    # Paso 2: los cuadrados medios se obtienen dividiendo cada SC entre sus grados de libertad.
    # Fórmulas: CM = SC/gl; F = CM_tratamientos/CM_error; SC_total = SC_tratamientos + SC_error.
    tabla["gl"] = tabla["gl"].astype(int)
    tabla["CM"] = tabla["SC"] / tabla["gl"]
    tabla = tabla.rename_axis("Fuente").reset_index()
    tabla = tabla[["Fuente", "gl", "SC", "CM", "F", "p-valor"]]

    # Paso 3: el total corregido reúne las sumas de cuadrados y grados de libertad de las dos fuentes.
    fila_total = pd.DataFrame(
        [
            {
                "Fuente": "Total",
                "gl": int(tabla["gl"].sum()),
                "SC": float(tabla["SC"].sum()),
                "CM": np.nan,
                "F": np.nan,
                "p-valor": np.nan,
            }
        ]
    )
    return pd.concat([tabla, fila_total], ignore_index=True)


def resumen_tratamientos(
    df: pd.DataFrame, col_trat: str, col_resp: str
) -> pd.DataFrame:
    """Resume el número de réplicas y la respuesta por tratamiento.

    Args:
        df: Datos del experimento.
        col_trat: Nombre de la columna que identifica los tratamientos.
        col_resp: Nombre de la columna con la respuesta.

    Returns:
        Un DataFrame con tratamiento, n, total, media y desviación estándar.

    Raises:
        ValueError: Si los datos no cumplen las validaciones básicas del DCA.
    """
    # Paso 1: se exige una estructura válida para que cada resumen represente un tratamiento replicado.
    errores = validar_dca(df, col_trat, col_resp)
    if errores:
        raise ValueError("No se puede resumir el DCA: " + " ".join(errores))

    # Paso 2: se convierten las respuestas y se agrupan las observaciones por tratamiento.
    # Fórmulas: n_i = cantidad de observaciones; total_i = ΣY_ij; media_i = ΣY_ij/n_i;
    # s_i = sqrt(Σ(Y_ij - media_i)^2/(n_i - 1)).
    datos = df[[col_trat, col_resp]].copy()
    datos[col_resp] = pd.to_numeric(datos[col_resp], errors="raise")
    resumen = (
        datos.groupby(col_trat, dropna=False)[col_resp]
        .agg(["count", "sum", "mean", "std"])
        .reset_index()
        .rename(
            columns={
                "count": "n",
                "sum": "total",
                "mean": "media",
                "std": "desviación estándar",
            }
        )
    )
    return resumen[
        [col_trat, "n", "total", "media", "desviación estándar"]
    ]


def coeficiente_variacion(
    modelo: RegressionResultsWrapper, df: pd.DataFrame, col_resp: str
) -> float:
    """Calcula el coeficiente de variación del DCA en porcentaje.

    Args:
        modelo: Modelo OLS ajustado para un DCA.
        df: Datos del experimento.
        col_resp: Nombre de la columna con la respuesta.

    Returns:
        El coeficiente de variación como porcentaje.

    Raises:
        ValueError: Si falta la respuesta o su media general es cero.
    """
    # Paso 1: se obtiene la media general de la respuesta en todas las unidades experimentales.
    if col_resp not in df.columns:
        raise ValueError(f"No se encontró la columna de respuesta '{col_resp}'.")
    media_general = float(pd.to_numeric(df[col_resp], errors="raise").mean())
    if media_general == 0:
        raise ValueError("No se puede calcular el CV cuando la media general es cero.")

    # Paso 2: se usa el cuadrado medio del error como estimación de la varianza residual.
    # Fórmula: CV (%) = sqrt(CME) / media_general × 100.
    cuadrado_medio_error = float(modelo.mse_resid)
    return float(np.sqrt(cuadrado_medio_error) / media_general * 100)


def tukey(
    df: pd.DataFrame,
    col_trat: str,
    col_resp: str,
    alfa: float = 0.05,
) -> tuple[pd.DataFrame, float]:
    """Compara las medias con Tukey y calcula una DMS para el diseño.

    Args:
        df: Datos del experimento.
        col_trat: Nombre de la columna que identifica los tratamientos.
        col_resp: Nombre de la columna con la respuesta.
        alfa: Nivel de significancia entre cero y uno.

    Returns:
        Una tupla con la tabla de comparaciones de Tukey en español y la DMS.

    Raises:
        ValueError: Si alfa o los datos no cumplen las condiciones del análisis.
    """
    # Paso 1: se valida alfa y la estructura del DCA antes de comparar tratamientos.
    if not 0 < alfa < 1:
        raise ValueError("El nivel alfa debe estar entre cero y uno.")
    errores = validar_dca(df, col_trat, col_resp)
    if errores:
        raise ValueError("No se puede ejecutar Tukey: " + " ".join(errores))

    # Paso 2: Tukey compara cada par de medias usando el error residual del modelo.
    # Fórmula de Tukey: diferencia estudentizada = |media_i - media_j| / error estándar.
    datos = df[[col_trat, col_resp]].copy()
    datos[col_resp] = pd.to_numeric(datos[col_resp], errors="raise")
    resultado = pairwise_tukeyhsd(
        endog=datos[col_resp], groups=datos[col_trat], alpha=alfa
    )
    tabla = pd.DataFrame(
        resultado._results_table.data[1:],
        columns=resultado._results_table.data[0],
    ).rename(
        columns={
            "group1": "Tratamiento 1",
            "group2": "Tratamiento 2",
            "meandiff": "Diferencia de medias",
            "p-adj": "p-valor ajustado",
            "lower": "Límite inferior",
            "upper": "Límite superior",
            "reject": "Diferencia significativa",
        }
    )
    for columna in (
        "Diferencia de medias",
        "p-valor ajustado",
        "Límite inferior",
        "Límite superior",
    ):
        tabla[columna] = pd.to_numeric(tabla[columna])
    tabla["Diferencia significativa"] = (
        tabla["Diferencia significativa"]
        .astype(str)
        .str.lower()
        .map({"true": "Sí", "false": "No"})
    )

    # Paso 3: se estima CME y glE; si faltan réplicas iguales se usa la réplica armónica como aproximación.
    # Fórmula: DMS = q(1-alfa; t; glE) × sqrt(CME/r), con r = t / Σ(1/n_i) si no hay balance.
    modelo = ajustar_dca(datos, col_trat, col_resp)
    cuadrado_medio_error = float(modelo.mse_resid)
    grados_libertad_error = float(modelo.df_resid)
    conteos = datos.groupby(col_trat).size()
    numero_tratamientos = int(conteos.size)
    balanceado = conteos.nunique() == 1
    if balanceado:
        replicas = float(conteos.iloc[0])
    else:
        replicas = float(numero_tratamientos / np.sum(1 / conteos.to_numpy(dtype=float)))
        aviso = "El diseño no está balanceado; la DMS calculada es aproximada."
        warnings.warn(aviso, UserWarning, stacklevel=2)
        tabla.attrs["aviso"] = aviso

    cuantil = float(
        studentized_range.ppf(1 - alfa, numero_tratamientos, grados_libertad_error)
    )
    dms = float(cuantil * np.sqrt(cuadrado_medio_error / replicas))
    return tabla, dms


def interpretar_dca(tabla: pd.DataFrame, alfa: float = 0.05) -> str:
    """Explica la decisión sobre la hipótesis de igualdad de medias.

    Args:
        tabla: Tabla ANOVA con las columnas Fuente y p-valor.
        alfa: Nivel de significancia usado para la decisión.

    Returns:
        Una interpretación breve en español para apoyar la decisión agronómica.

    Raises:
        ValueError: Si falta la fila de tratamientos o alfa está fuera de rango.
    """
    # Paso 1: se localiza el p-valor del factor; H₀ establece que todas las medias son iguales.
    if not 0 < alfa < 1:
        raise ValueError("El nivel alfa debe estar entre cero y uno.")
    if "Fuente" not in tabla.columns or "p-valor" not in tabla.columns:
        raise ValueError("La tabla debe incluir las columnas 'Fuente' y 'p-valor'.")
    p_valor_tratamientos = tabla.loc[
        tabla["Fuente"] == "Tratamientos", "p-valor"
    ]
    if p_valor_tratamientos.empty:
        raise ValueError("La tabla no contiene una fila de Tratamientos.")

    # Paso 2: la regla de decisión compara p con alfa, es decir, rechazar H₀ si p ≤ alfa.
    p_valor = float(p_valor_tratamientos.iloc[0])
    if p_valor <= alfa:
        return (
            "Se rechaza H₀: hay evidencia de que al menos una media de tratamiento "
            "difiere. Para decidir en campo, identifica qué tratamientos difieren "
            "y considera también su relevancia agronómica."
        )
    return (
        "No se rechaza H₀: no hay evidencia suficiente para afirmar que las medias "
        "de los tratamientos difieren. Esto no demuestra que sean iguales; contrasta "
        "la decisión con los supuestos y el criterio agronómico."
    )