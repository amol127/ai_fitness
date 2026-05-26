# Architecture

## Flow

Transactions CSV
        ↓
Normalization Engine
        ↓
Matching Logic
        ↓
Gap Detection
        ↓
FastAPI APIs
        ↓
React Dashboard

## Gap Types Detected

- Late Settlement
- Duplicate Settlement
- Rounding Difference
- Orphan Refund

## Backend

- FastAPI
- Pandas
- Python

## Frontend

- React
- Tailwind CSS
- Recharts

## Scalability Concerns

Current implementation loads all records into memory.
Production systems should use:
- streaming pipelines
- database indexing
- pagination
- async processing
- distributed reconciliation workers