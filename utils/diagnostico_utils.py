"""Diagnósticos de supuestos para modelos de Diseño Completamente al Azar."""

from collections.abc import Sequence

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from scipy.stats import levene, probplot, shapiro
from statsmodels.regression.linear_model import RegressionResultsWrapper

from utils.anova_utils import validar_dca


def residuos_y_ajustados(
    modelo: RegressionResultsWrapper,
) -> tuple[pd.Series, pd.Series]:
    """Extrae residuos y valores ajustados del modelo.

    Args:
        modelo: Modelo OLS ajustado para el DCA.

    Returns:
        Una tupla con los residuos y los valores ajustados, en ese orden.
    """
    # Paso 1: se extrae cada respuesta predicha para compararla con la observada.
    ajustados = pd.Series(modelo.fittedvalues, name="Valor ajustado")

    # Paso 2: se calcula el residuo de cada unidad para revisar el comportamiento del error.
    # Fórmula: e_i = y_i - ŷ_i, donde y_i es la respuesta observada y ŷ_i la ajustada.
    residuos = pd.Series(modelo.resid, name="Residuo")
    return residuos, ajustados


def prueba_shapiro(
    residuos: Sequence[float] | pd.Series | np.ndarray,
    alfa: float = 0.05,
) -> tuple[float, float, str]:
    """Evalúa la normalidad de los residuos con Shapiro-Wilk.

    Args:
        residuos: Residuos del modelo DCA.
        alfa: Nivel de significancia para la conclusión.

    Returns:
        Estadístico W, p-valor y conclusión en español.

    Raises:
        ValueError: Si alfa no está entre cero y uno o hay menos de tres residuos.
    """
    # Paso 1: se comprueba que alfa y la cantidad de residuos permitan la prueba.
    if not 0 < alfa < 1:
        raise ValueError("El nivel alfa debe estar entre cero y uno.")
    valores = np.asarray(residuos, dtype=float)
    if valores.size < 3:
        raise ValueError("Shapiro-Wilk requiere al menos tres residuos.")
    if not np.isfinite(valores).all():
        raise ValueError("Los residuos deben ser finitos para aplicar Shapiro-Wilk.")

    # Paso 2: W compara el orden de los residuos con el esperado bajo normalidad.
    # Fórmula: W = [Σ(a_i · x_(i))]² / Σ(x_i - x̄)², calculada por SciPy.
    estadistico, p_valor = shapiro(valores)
    if p_valor < alfa:
        conclusion = (
            "Se rechaza la normalidad: hay evidencia de que los residuos "
            "se apartan de una distribución normal."
        )
    else:
        conclusion = (
            "No se rechaza la normalidad: no hay evidencia suficiente para afirmar "
            "que los residuos se apartan de una distribución normal."
        )
    return float(estadistico), float(p_valor), conclusion


def prueba_levene(
    df: pd.DataFrame,
    col_trat: str,
    col_resp: str,
    alfa: float = 0.05,
) -> tuple[float, float, str]:
    """Evalúa la igualdad de varianzas entre tratamientos con Levene.

    Args:
        df: Datos del experimento.
        col_trat: Nombre de la columna de tratamientos.
        col_resp: Nombre de la columna de respuesta.
        alfa: Nivel de significancia para la conclusión.

    Returns:
        Estadístico de Levene, p-valor y conclusión en español.

    Raises:
        ValueError: Si alfa o los datos no cumplen las condiciones del DCA.
    """
    # Paso 1: se valida la estructura para evitar omitir tratamientos o réplicas.
    if not 0 < alfa < 1:
        raise ValueError("El nivel alfa debe estar entre cero y uno.")
    errores = validar_dca(df, col_trat, col_resp)
    if errores:
        raise ValueError("No se puede aplicar Levene: " + " ".join(errores))

    # Paso 2: se separa la respuesta por tratamiento para comparar su dispersión.
    datos = df[[col_trat, col_resp]].copy()
    datos[col_resp] = pd.to_numeric(datos[col_resp], errors="raise")
    grupos = [
        grupo[col_resp].to_numpy(dtype=float)
        for _, grupo in datos.groupby(col_trat, sort=False)
    ]

    # Paso 3: center='median' compara desviaciones absolutas respecto a cada mediana.
    # Fórmula: Z_ij = |Y_ij - mediana_i|; Levene evalúa si la media de Z difiere entre tratamientos.
    estadistico, p_valor = levene(*grupos, center="median")
    if p_valor < alfa:
        conclusion = (
            "Se rechaza la igualdad de varianzas: hay evidencia de variabilidad "
            "diferente entre tratamientos."
        )
    else:
        conclusion = (
            "No se rechaza la igualdad de varianzas: no hay evidencia suficiente "
            "de variabilidad diferente entre tratamientos."
        )
    return float(estadistico), float(p_valor), conclusion


def grafico_residuos_vs_ajustados(
    ajustados: Sequence[float] | pd.Series | np.ndarray,
    residuos: Sequence[float] | pd.Series | np.ndarray,
) -> go.Figure:
    """Crea un gráfico de residuos frente a valores ajustados.

    Args:
        ajustados: Valores predichos por el modelo.
        residuos: Diferencias entre respuestas observadas y ajustadas.

    Returns:
        Figura Plotly para inspeccionar patrones y dispersión residual.

    Raises:
        ValueError: Si las series no tienen igual longitud o contienen valores no finitos.
    """
    # Paso 1: se convierten las series y se comprueba que cada ajuste tenga su residuo correspondiente.
    valores_ajustados = np.asarray(ajustados, dtype=float)
    valores_residuales = np.asarray(residuos, dtype=float)
    if valores_ajustados.size != valores_residuales.size or valores_ajustados.size == 0:
        raise ValueError("Ajustados y residuos deben tener la misma longitud no vacía.")
    if not np.isfinite(valores_ajustados).all() or not np.isfinite(valores_residuales).all():
        raise ValueError("Ajustados y residuos deben contener valores finitos.")

    # Paso 2: se representa ŷ_i en el eje x y e_i = y_i - ŷ_i en el eje y; la línea guía marca e_i = 0.
    figura = go.Figure(
        data=go.Scatter(
            x=valores_ajustados,
            y=valores_residuales,
            mode="markers",
            name="Observaciones",
        )
    )
    figura.add_hline(y=0, line_dash="dash", line_color="#5b6573")
    figura.update_layout(
        title="Residuos frente a valores ajustados",
        xaxis_title="Valores ajustados",
        yaxis_title="Residuos",
        showlegend=False,
    )
    return figura


def grafico_qq(
    residuos: Sequence[float] | pd.Series | np.ndarray,
) -> go.Figure:
    """Crea un gráfico Q-Q normal para los residuos del modelo.

    Args:
        residuos: Residuos del modelo DCA.

    Returns:
        Figura Plotly que compara cuantiles residuales y normales teóricos.

    Raises:
        ValueError: Si hay menos de tres residuos o valores no finitos.
    """
    # Paso 1: se verifica que haya suficientes residuos válidos para comparar cuantiles.
    valores = np.asarray(residuos, dtype=float)
    if valores.size < 3:
        raise ValueError("El gráfico Q-Q requiere al menos tres residuos.")
    if not np.isfinite(valores).all():
        raise ValueError("Los residuos deben ser finitos para crear el gráfico Q-Q.")

    # Paso 2: los cuantiles observados se comparan con los de una normal; se agrega la recta de referencia.
    # Fórmula de cuantiles teóricos: q_i = Φ⁻¹((i - 0.5)/n), según el orden de los residuos.
    (cuantiles_teoricos, cuantiles_observados), (pendiente, intercepto, _) = probplot(
        valores, dist="norm", fit=True
    )
    extremos = np.array([cuantiles_teoricos.min(), cuantiles_teoricos.max()])
    figura = go.Figure(
        data=go.Scatter(
            x=cuantiles_teoricos,
            y=cuantiles_observados,
            mode="markers",
            name="Residuos",
        )
    )
    figura.add_trace(
        go.Scatter(
            x=extremos,
            y=pendiente * extremos + intercepto,
            mode="lines",
            name="Referencia normal",
        )
    )
    figura.update_layout(
        title="Gráfico Q-Q de los residuos",
        xaxis_title="Cuantiles teóricos normales",
        yaxis_title="Cuantiles observados de los residuos",
    )
    return figura
