# Backend architecture

PennyWise uses a layered modular-monolith architecture. Features remain in one
FastAPI application and one relational database, but HTTP handling, business
rules, persistence models, and request/response contracts have separate homes.

## Layers

```text
frontend/src/app and frontend/src/components
                 |
                 | HTTPS / JSON
                 v
backend/routes/          HTTP endpoints, auth dependencies, status codes
                 |
                 v
backend/services/        Business rules and feature workflows
                 |
                 v
backend/models/          SQLAlchemy persistence models
                 |
                 v
backend/db.py             Database engine and session lifecycle