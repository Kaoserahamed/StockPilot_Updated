# StockPilot_Updated Authentication Module

## Overview
Authentication system for cashier/manager/admin roles with OAuth2, JWT, and PIN-based cashier login.

## Files
- `services/pos/auth.py` - Authentication logic
- `services/pos/models.py` - User and role models
- `services/pos/middleware.py` - Auth middleware and RBAC
- `services/pos/routes/auth.py` - Auth API routes
- `services/pos/pin_auth.py` - PIN-based cashier login

## Features
- Cashier, manager, and admin account registration/login
- JWT-based session management
- OAuth2 provider integration
- Role-Based Access Control (RBAC)
- PIN-based cashier login for POS terminals
- Password hashing with bcrypt
- Session timeout handling

## Tech Stack
- Python/FastAPI
- PostgreSQL
- JWT (PyJWT)
- OAuth2
- bcrypt for password hashing

## Day 5 Outcome
Authentication module implemented. 1 PR created targeting development.