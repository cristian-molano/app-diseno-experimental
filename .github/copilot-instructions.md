# Instrucciones del repositorio

## Contexto del proyecto
- Proyecto: aplicación de Diseño Experimental desarrollada en Python y Streamlit para el curso de Diseño Experimental de Ingeniería Agrícola en la Universidad de Sucre.

## Estructura
- `app.py`: portada de la aplicación.
- `pages/`: un archivo por cada diseño experimental.
- `utils/`: funciones reutilizables; incluir `__init__.py`.
- `data/`: archivos CSV de ejemplo.
- `verificacion/`: scripts de R para verificar los análisis.

## Idioma y claridad pedagógica
- Escribe todo el código, los comentarios, los docstrings y los mensajes de la interfaz en español.
- Añade en cada paso estadístico un comentario que explique qué se calcula y por qué, con explicaciones adecuadas para estudiantes de Ingeniería Agrícola.
- Define las funciones con type hints y docstrings en estilo Google.

## Dependencias permitidas
- Usa únicamente `streamlit`, `pandas`, `numpy`, `scipy`, `statsmodels`, `plotly` y `openpyxl`.
- No agregues otras librerías sin pedir permiso.

## Métodos estadísticos
- Ajusta los modelos ANOVA con `statsmodels.formula.api.ols` y calcula las tablas con `statsmodels.stats.anova.anova_lm(typ=2)`.
- Realiza las comparaciones de Tukey con `statsmodels.stats.multicomp.pairwise_tukeyhsd`.
- No inventes resultados: todos los números presentados deben provenir del cálculo ejecutado.

## Verificación
- Antes de terminar una tarea, ejecuta el código y corrige los errores que aparezcan.
