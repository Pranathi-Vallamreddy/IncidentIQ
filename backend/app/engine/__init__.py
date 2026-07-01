"""IncidentIQ analysis engine.

Framework-independent. Given raw log lines, produces parsed events, mined
templates, clusters, anomaly scores, severities, incidents and correlations.
No FastAPI / SQLAlchemy imports live in this package.
"""
